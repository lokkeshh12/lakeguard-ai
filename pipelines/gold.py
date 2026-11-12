"""Gold daily order metrics from conformed Silver data."""
import argparse
from pyspark.sql import SparkSession, functions as F

def run(silver: str, gold: str) -> None:
    """Recompute daily business aggregates from canonical Silver state."""
    spark = SparkSession.builder.getOrCreate()
    result = (spark.table(silver).groupBy(F.to_date("event_ts").alias("order_date"))
              .agg(F.count("order_id").alias("order_count"),
                   F.sum("amount").alias("gross_amount")))
    result.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable(gold)

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--silver", required=True)
    p.add_argument("--gold", required=True)
    run(**vars(p.parse_args()))
