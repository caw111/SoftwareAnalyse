FROM eclipse-temurin:21-jdk-alpine AS build
WORKDIR /workspace
COPY gradle gradle
COPY gradlew settings.gradle build.gradle gradle.properties ./
RUN sed -i 's/\r$//' gradlew && chmod +x gradlew
COPY src src
RUN --mount=type=cache,target=/root/.gradle ./gradlew --no-daemon bootJar

FROM eclipse-temurin:21-jre-alpine
RUN addgroup -S app && adduser -S -G app -u 10001 app
WORKDIR /app
COPY --from=build --chown=10001:10001 /workspace/build/libs/academic-platform-api.jar app.jar
USER 10001:10001
ENV APP_DEMO=false SERVER_ADDRESS=0.0.0.0 MANAGEMENT_ADDRESS=0.0.0.0 \
    JAVA_TOOL_OPTIONS="-XX:MaxRAMPercentage=65 -XX:InitialRAMPercentage=20 -XX:+ExitOnOutOfMemoryError -Dfile.encoding=UTF-8"
EXPOSE 8080 8081
ENTRYPOINT ["java", "-jar", "/app/app.jar"]
