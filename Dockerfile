FROM maven:3.9.6-eclipse-temurin-17 as builder
WORKDIR /app
COPY complete /app
RUN chmod +x mvnw && ./mvnw clean package -DskipTests

FROM eclipse-temurin:17-jdk
WORKDIR /app
COPY --from=builder /app/target/*.jar app.jar
EXPOSE 777
CMD ["java", "-jar", "app.jar", "--server.port=777"]