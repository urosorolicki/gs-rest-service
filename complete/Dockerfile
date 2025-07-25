FROM openjdk:17-jdk-slim
COPY target/rest-service-complete-0.0.1-SNAPSHOT.jar app.jar
EXPOSE 7777
ENTRYPOINT ["java", "-jar", "/app.jar"]
