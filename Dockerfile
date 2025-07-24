FROM eclipse-temurin:17-jdk-alpine

WORKDIR /app

# Copy source code and wrapper scripts
COPY complete /app/complete
COPY complete/.mvn /app/complete/.mvn
COPY complete/mvnw /app/complete/mvnw
COPY complete/pom.xml /app/complete/pom.xml

# Make mvnw executable and build the project
WORKDIR /app/complete
RUN chmod +x mvnw && ./mvnw package -DskipTests

# Expose internal app port
EXPOSE 8080

# Run the app
CMD ["java", "-jar", "target/gs-rest-service-0.1.0.jar"]
