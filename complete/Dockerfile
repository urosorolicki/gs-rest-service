FROM openjdk:17-jdk-slim
ARG JAR_FILE=target/gs-rest-service-0.1.0.jar
COPY ${JAR_FILE} app.jar
EXPOSE 7777
ENTRYPOINT ["java","-jar","/app.jar"]
