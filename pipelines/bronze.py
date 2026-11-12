"""Incremental raw ingestion using Auto Loader and rescued data."""
import argparse
from pyspark.sql import SparkSession, functions as F


def run(source: str, target: str, checkpoint: str, schema_location: str) -> None:
    """Run an available-now incremental ingestion into Bronze Delta."""
    spark = SparkSession.builder.getOrCreate()
    stream = (spark.readStream.format("cloudFiles")
              .option("cloudFiles.format", "json")
              .option("cloudFiles.schemaLocation", schema_location)
              .option("cloudFiles.schemaEvolutionMode", "rescue")
              .option("rescuedDataColumn", "_rescued_data")
              .load(source)
              .withColumn("_ingested_at", F.current_timestamp())
              .withColumn("_source_file", F.col("_metadata.file_path")))
    (stream.writeStream.format("delta").option("checkpointLocation", checkpoint)
     .trigger(availableNow=True).toTable(target).awaitTermination())

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    for name in ("source", "target", "checkpoint", "schema_location"):
        p.add_argument(f"--{name.replace('_', '-')}", required=True)
    run(**vars(p.parse_args()))
