FROM metabase/metabase:v0.63.1
# Driver comunitario Arrow Flight SQL (necesario para Dremio OSS vía puerto 32010).
ADD https://github.com/J0hnG4lt/metabase-flightsql-driver/releases/download/0.6.1/arrow-flight-sql.metabase-driver.jar /plugins/arrow-flight-sql.metabase-driver.jar
RUN chmod 644 /plugins/arrow-flight-sql.metabase-driver.jar
ENV JAVA_OPTS="--add-opens=java.base/java.nio=ALL-UNNAMED --add-opens=java.base/sun.nio.ch=ALL-UNNAMED --sun-misc-unsafe-memory-access=allow"
