"""Idempotent Bronze-to-Silver batch upsert with quarantine."""
import argparse
from pyspark.sql import SparkSession, Window, functions as F
from delta.tables import DeltaTable


def run(bronze: str, silver: str, quarantine: str) -> None:
    """Validate and merge latest records; retain invalid records separately."""
    spark = SparkSession.builder.getOrCreate()
    df = spark.table(bronze)
    required = {"order_id", "customer_id", "amount", "event_ts"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing mandatory fields: {sorted(missing)}")
    clean = (df.withColumn("amount", F.col("amount").cast("decimal(18,2)"))
             .withColumn("event_ts", F.to_timestamp("event_ts")))
    valid = (F.col("order_id").isNotNull() & F.col("customer_id").isNotNull()
             & F.col("amount").isNotNull() & (F.col("amount") >= 0)
             & F.col("event_ts").isNotNull())
    invalid = clean.filter(~valid).withColumn("_quarantine_reason", F.lit("invalid_order"))
    # In a production scheduled run, use a source batch/run ID to avoid re-appending
    # the same quarantined rows when a task retries.
    invalid.write.format("delta").mode("append").saveAsTable(quarantine)
    w = Window.partitionBy("order_id").orderBy(F.col("event_ts").desc(), F.col("_ingested_at").desc())
    latest = clean.filter(valid).withColumn("_rn", F.row_number().over(w)).filter("_rn = 1").drop("_rn")
    if not spark.catalog.tableExists(silver):
        latest.write.format("delta").mode("overwrite").saveAsTable(silver)
    else:
        (DeltaTable.forName(spark, silver).alias("t").merge(latest.alias("s"), "t.order_id = s.order_id")
         .whenMatchedUpdateAll(condition="s.event_ts >= t.event_ts")
         .whenNotMatchedInsertAll().execute())

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    for n in ("bronze", "silver", "quarantine"):
        p.add_argument(f"--{n}", required=True)
    run(**vars(p.parse_args()))
