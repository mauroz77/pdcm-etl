from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.types import (
    StructType,
    IntegerType,
    StringType,
    StructField,
)
from pyspark.sql.functions import col, lit, expr, regexp_extract, when, concat, concat_ws, collect_list


# Adds links to other resources with aditional information about the model
def add_model_links(
    model_information_df: DataFrame, raw_external_model_ids_df: DataFrame
):
    spark: SparkSession = SparkSession.builder.getOrCreate()

    # Schema for the df each method is going to return
    schema = StructType(
        [
            StructField("id", IntegerType(), False),
            StructField("resource_label", StringType(), False),
            StructField("link_label", StringType(), False),
            StructField("type", StringType(), False),
            StructField("link", StringType(), True),
        ]
    )
    all_links_df = spark.createDataFrame(data=[], schema=schema)
    resources_list = [row.asDict() for row in raw_external_model_ids_df.collect()]
    for resource in resources_list:

        if resource["link_building_method"] == "COSMICLink":
            print("Create links for COSMIC")
            tmp_df = find_cosmic_links(model_information_df, resource)
            all_links_df = all_links_df.unionAll(tmp_df)

        if resource["link_building_method"] == "DeepMapLink":
            print("Create links for DeepMap")

        if resource["link_building_method"] == "CellosaurusLink":
            print("Create links for Cellosaurus")

        if resource["link_building_method"] == "CancerCellLinesLink":
            print("Create links for CancerCellLines")

    model_ids_links_column_df = create_model_links_column(all_links_df)

    # Join back to the original data frame to add the new column to it
    model_information_df = model_information_df.join(model_ids_links_column_df, on=["id"], how="left")
    model_information_df.show(truncate=False)

    return model_information_df


# If the external ID field has COSMC then use the model_name to generate the link
def find_cosmic_links(model_information_df: DataFrame, resource_definition) -> DataFrame:

    data_df = model_information_df.select("id", "external_ids", "model_name")
    data_df = data_df.withColumn(
        "resource_label", lit(resource_definition["resource_label"])
    )
    data_df = data_df.withColumn("type", lit(resource_definition["type"]))
    data_df = data_df.withColumn("link_label", col("model_name"))
    data_df = data_df.where("upper(external_ids) like '%COSMIC%'")

    links_df = data_df.withColumn(
        "link", lit(resource_definition["link_template"])
    )
    links_df = links_df.withColumn(
        "link",
        when(col("model_name") == "", None).otherwise(
            expr("regexp_replace(link, 'model_name', model_name)")
        ),
    )
    return links_df.select("id", "resource_label", "link_label", "type", "link")


# Takes a df with the columns <"id", "resource_label", "type", "link"> and returns a df
# with columns <"id", "model_ids_links"> where "model_ids_links" is a JSON with the information to build links in the UI
# with an array of objects in the format <>
def create_model_links_column(links_df: DataFrame) -> DataFrame:
    links_json_entry_column_df = links_df.withColumn(
        "json_entry",
        concat(lit("{"),
               lit("\"type\": "), lit("\""), col("type"), lit("\", "),
               lit("\"resource_label\": "), lit("\""), col("resource_label"), lit("\", "),
                lit("\"link_label\": "), lit("\""), col("link_label"), lit("\", "),
               lit("\"link\": "), lit("\""), col("link"), lit("\""),
               concat(lit("}"))))
    model_ids_links_column_df = links_json_entry_column_df.groupby("id").agg(
        concat_ws(", ", collect_list(links_json_entry_column_df.json_entry)).alias("other_model_links"))
    model_ids_links_column_df = model_ids_links_column_df.withColumn(
        "other_model_links",
        concat(lit("["), col("other_model_links"), concat(lit("]"))))
    return model_ids_links_column_df

