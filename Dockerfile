# Use lightweight JDK base image
FROM eclipse-temurin:17-jdk-alpine

# Set working directory
WORKDIR /app

# Copy code
COPY complete /app/complete
COPY complete/pom.xml /app/complete/pom.xml
COPY complete/mvnw /app/complete/mvnw
COPY complete/.mvn /app/complete/.mvn

# Build the Spring Boot app
WORKDIR /app/complete
RUN chmod +x mvnw && ./mvnw clean package -DskipTests

# Expose port 8080 (Render maps it to 777)
EXPOSE 8080

# Run the app
CMD ["java", "-jar", "target/gs-rest-service-0.1.0.jar"]
