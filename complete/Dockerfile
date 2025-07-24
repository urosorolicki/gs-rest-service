# Multi-stage build for smallest possible image
FROM maven:3.9.6-eclipse-temurin-17-alpine AS builder

# Set working directory
WORKDIR /app

# Copy POM file first for better layer caching
COPY pom.xml .

# Download dependencies (this layer will be cached unless pom.xml changes)
RUN mvn dependency:go-offline -B

# Copy source code
COPY src ./src

# Build the application
RUN mvn clean package -DskipTests

# Runtime stage with minimal JRE
FROM eclipse-temurin:17-jre-alpine

# Create non-root user for security
RUN addgroup -g 1001 -S appgroup && \
    adduser -S -D -G appgroup -u 1001 appuser

# Set working directory
WORKDIR /app

# Copy JAR from builder stage
COPY --from=builder /app/target/*.jar app.jar

# Change ownership to non-root user
RUN chown appuser:appgroup app.jar

# Switch to non-root user
USER appuser

# Expose port 777 (service will be mapped from 8080 to 777)
EXPOSE 777

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:777/greeting || exit 1

# Run the application on port 777
ENTRYPOINT ["java", "-server", "-XX:+UseContainerSupport", "-XX:MaxRAMPercentage=75.0", "-Dserver.port=777", "-jar", "app.jar"]
