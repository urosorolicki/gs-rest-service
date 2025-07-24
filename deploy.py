#!/usr/bin/env python3

"""
GS Rest Service Deployment Script
Author: DevOps Team
Description: Deploys the gs-rest-service Docker container to a remote server
"""

import argparse
import subprocess
import sys
import time
import os
from datetime import datetime
from typing import Optional
import paramiko
import requests


class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'  # No Color


class Logger:
    @staticmethod
    def log(message: str):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"{Colors.BLUE}[{timestamp}]{Colors.NC} {message}")
    
    @staticmethod
    def error(message: str):
        print(f"{Colors.RED}[ERROR]{Colors.NC} {message}", file=sys.stderr)
    
    @staticmethod
    def success(message: str):
        print(f"{Colors.GREEN}[SUCCESS]{Colors.NC} {message}")
    
    @staticmethod
    def warning(message: str):
        print(f"{Colors.YELLOW}[WARNING]{Colors.NC} {message}")


class DockerDeployer:
    def __init__(self, config: dict):
        self.config = config
        self.ssh_client = None
        
    def __enter__(self):
        if not self.config['local_deploy'] and not self.config['dry_run']:
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            try:
                self.ssh_client.connect(
                    hostname=self.config['deploy_server'],
                    username=self.config['ssh_user'],
                    port=self.config['ssh_port'],
                    timeout=30
                )
                Logger.log(f"Connected to {self.config['deploy_server']}")
            except Exception as e:
                Logger.error(f"Failed to connect to server: {e}")
                raise
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.ssh_client:
            self.ssh_client.close()
    
    def execute_command(self, command: str) -> tuple:
        """Execute command locally or remotely"""
        if self.config['dry_run']:
            location = "locally" if self.config['local_deploy'] else f"on {self.config['deploy_server']}"
            Logger.log(f"DRY RUN: Would execute {location}: {command}")
            return True, "", ""
        
        if self.config['local_deploy']:
            try:
                result = subprocess.run(
                    command, 
                    shell=True, 
                    capture_output=True, 
                    text=True, 
                    timeout=300
                )
                return result.returncode == 0, result.stdout, result.stderr
            except subprocess.TimeoutExpired:
                Logger.error("Command timed out")
                return False, "", "Command timed out"
        else:
            try:
                stdin, stdout, stderr = self.ssh_client.exec_command(command, timeout=300)
                exit_code = stdout.channel.recv_exit_status()
                return exit_code == 0, stdout.read().decode(), stderr.read().decode()
            except Exception as e:
                Logger.error(f"SSH command failed: {e}")
                return False, "", str(e)
    
    def build_image(self) -> bool:
        """Build Docker image"""
        Logger.log(f"Building Docker image: {self.config['docker_image']}")
        
        dockerfile_path = os.path.join(os.path.dirname(__file__), 'complete', 'Dockerfile')
        if not os.path.exists(dockerfile_path):
            Logger.error(f"Dockerfile not found at {dockerfile_path}")
            return False
        
        if self.config['dry_run']:
            Logger.log(f"DRY RUN: Would build image with: docker build -t {self.config['docker_image']} complete/")
            return True
        
        try:
            result = subprocess.run(
                ['docker', 'build', '-t', self.config['docker_image'], 'complete/'],
                cwd=os.path.dirname(__file__),
                capture_output=True,
                text=True,
                timeout=600
            )
            
            if result.returncode == 0:
                Logger.success("Docker image built successfully")
                return True
            else:
                Logger.error(f"Docker build failed: {result.stderr}")
                return False
        except subprocess.TimeoutExpired:
            Logger.error("Docker build timed out")
            return False
        except Exception as e:
            Logger.error(f"Docker build error: {e}")
            return False
    
    def deploy_application(self) -> bool:
        """Deploy the application"""
        Logger.log(f"Starting deployment of {self.config['docker_image']}")
        
        # Stop existing container
        Logger.log("Stopping existing container (if running)...")
        self.execute_command(f"docker stop {self.config['container_name']} || true")
        self.execute_command(f"docker rm {self.config['container_name']} || true")
        
        # Pull image if not building locally
        if not self.config['build_image'] and not self.config['local_deploy']:
            Logger.log("Pulling Docker image on remote server...")
            success, stdout, stderr = self.execute_command(f"docker pull {self.config['docker_image']}")
            if not success:
                Logger.error(f"Failed to pull image: {stderr}")
                return False
        
        # Run new container
        Logger.log("Starting new container...")
        run_cmd = (
            f"docker run -d "
            f"--name {self.config['container_name']} "
            f"--restart unless-stopped "
            f"-p {self.config['app_port']}:777 "
            f"-e SPRING_PROFILES_ACTIVE=production "
            f"{self.config['docker_image']}"
        )
        
        success, stdout, stderr = self.execute_command(run_cmd)
        if not success:
            Logger.error(f"Failed to start container: {stderr}")
            return False
        
        if not self.config['dry_run']:
            Logger.success("Container started successfully")
            Logger.log("Waiting for service to start...")
            time.sleep(30)
        
        return True
    
    def health_check(self) -> bool:
        """Perform health check"""
        if self.config['skip_health_check']:
            Logger.warning("Skipping health check")
            return True
        
        Logger.log("Performing health check...")
        
        if self.config['dry_run']:
            Logger.log(f"DRY RUN: Would perform health check on port {self.config['app_port']}")
            return True
        
        max_attempts = 5
        for attempt in range(1, max_attempts + 1):
            Logger.log(f"Health check attempt {attempt}/{max_attempts}")
            
            try:
                if self.config['local_deploy']:
                    url = f"http://localhost:{self.config['app_port']}/greeting"
                    response = requests.get(url, timeout=10)
                    if response.status_code == 200:
                        Logger.success("Health check passed - service is running!")
                        return True
                else:
                    health_cmd = f"curl -f http://localhost:{self.config['app_port']}/greeting"
                    success, stdout, stderr = self.execute_command(health_cmd)
                    if success:
                        Logger.success("Health check passed - service is running!")
                        return True
            except Exception as e:
                Logger.warning(f"Health check failed: {e}")
            
            if attempt < max_attempts:
                Logger.warning("Health check failed, retrying in 10 seconds...")
                time.sleep(10)
        
        Logger.error(f"Health check failed after {max_attempts} attempts")
        return False
    
    def get_status(self):
        """Get service status"""
        Logger.log("Getting service status...")
        
        if self.config['dry_run']:
            Logger.log("DRY RUN: Would check service status")
            return
        
        # Check container status
        success, stdout, stderr = self.execute_command(f"docker ps | grep {self.config['container_name']} || echo 'Container not running'")
        if stdout.strip():
            Logger.log(f"Container status: {stdout.strip()}")
        
        # Check service response
        try:
            if self.config['local_deploy']:
                url = f"http://localhost:{self.config['app_port']}/greeting"
                response = requests.get(url, timeout=5)
                Logger.log(f"Service response: {response.status_code} - {response.text}")
            else:
                success, stdout, stderr = self.execute_command(f"curl -s http://localhost:{self.config['app_port']}/greeting || echo 'Service not responding'")
                Logger.log(f"Service response: {stdout.strip()}")
        except Exception as e:
            Logger.log(f"Service not responding: {e}")


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='GS Rest Service Deployment Script',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 deploy.py --local --build
  python3 deploy.py --server myserver.com --user deploy --build
  python3 deploy.py --server 192.168.1.100 --image gs-rest-service:v1.0.0
        """
    )
    
    parser.add_argument('-s', '--server', help='Deployment server hostname/IP')
    parser.add_argument('-u', '--user', help='SSH username (default: current user)')
    parser.add_argument('-p', '--port', type=int, default=22, help='SSH port (default: 22)')
    parser.add_argument('-i', '--image', default='gs-rest-service:latest', help='Docker image to deploy')
    parser.add_argument('-c', '--container', default='gs-rest-service', help='Container name')
    parser.add_argument('--app-port', default='777', help='Application port (default: 777)')
    parser.add_argument('--local', action='store_true', help='Deploy locally instead of remote server')
    parser.add_argument('--build', action='store_true', help='Build Docker image before deployment')
    parser.add_argument('--no-health-check', action='store_true', help='Skip health check after deployment')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without executing')
    
    return parser.parse_args()


def main():
    """Main function"""
    args = parse_arguments()
    
    # Validate arguments
    if not args.local and not args.server:
        Logger.error("Deployment server must be specified unless using --local")
        sys.exit(1)
    
    # Prepare configuration
    config = {
        'deploy_server': args.server,
        'ssh_user': args.user or os.getenv('USER', 'root'),
        'ssh_port': args.port,
        'docker_image': args.image,
        'container_name': args.container,
        'app_port': args.app_port,
        'local_deploy': args.local,
        'build_image': args.build,
        'skip_health_check': args.no_health_check,
        'dry_run': args.dry_run
    }
    
    Logger.log("GS Rest Service Deployment Script Starting...")
    
    # Print configuration
    Logger.log("Deployment Configuration:")
    Logger.log(f"  Docker Image: {config['docker_image']}")
    Logger.log(f"  Container Name: {config['container_name']}")
    Logger.log(f"  Application Port: {config['app_port']}")
    Logger.log(f"  Local Deploy: {config['local_deploy']}")
    Logger.log(f"  Build Image: {config['build_image']}")
    Logger.log(f"  Dry Run: {config['dry_run']}")
    
    if not config['local_deploy']:
        Logger.log(f"  Deploy Server: {config['deploy_server']}")
        Logger.log(f"  SSH User: {config['ssh_user']}")
        Logger.log(f"  SSH Port: {config['ssh_port']}")
    
    try:
        with DockerDeployer(config) as deployer:
            # Build image if requested
            if config['build_image']:
                if not deployer.build_image():
                    sys.exit(1)
            
            # Deploy application
            if not deployer.deploy_application():
                sys.exit(1)
            
            # Health check
            if not deployer.health_check():
                sys.exit(1)
            
            # Show final status
            deployer.get_status()
            
            Logger.success("Deployment completed successfully!")
            if config['local_deploy']:
                Logger.log(f"Service should be available at: http://localhost:{config['app_port']}/greeting")
            else:
                Logger.log(f"Service should be available at: http://{config['deploy_server']}:{config['app_port']}/greeting")
    
    except KeyboardInterrupt:
        Logger.error("Deployment interrupted by user")
        sys.exit(1)
    except Exception as e:
        Logger.error(f"Deployment failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
