FROM eclipse-temurin:17-jdk-alpine AS build
WORKDIR /app
COPY complete/ /app/
RUN chmod +x mvnw
RUN ./mvnw clean package -DskipTests

FROM eclipse-temurin:17-jdk-alpine
WORKDIR /app
COPY --from=build /app/target/gs-rest-service-0.1.0.jar ./app.jar
EXPOSE 8080
CMD ["java", "-jar", "app.jar"]
