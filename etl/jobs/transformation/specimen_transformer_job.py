import sys

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import lit, col

from etl.jobs.util.cleaner import init_cap_and_trim_all
from etl.jobs.util.dataframe_functions import transform_to_fk
from etl.jobs.util.id_assigner import add_id


def main(argv):
    """
    Creates a parquet file with patient sample data.
    :param list argv: the list elements should be:
                    [1]: Parquet file path with raw model data
                    [2]: Parquet file path with engraftment site data
                    [3]: Parquet file path with engraftment type data
                    [4]: Parquet file path with engraftment material data
                    [5]: Parquet file path with model data
                    [5]: Parquet file path with patient sample data
                    [6]: Output file
    """
    raw_model_parquet_path = argv[1]
    engraftment_site_parquet_path = argv[2]
    engraftment_type_parquet_path = argv[3]
    engraftment_material_parquet_path = argv[4]
    host_strain_parquet_path = argv[5]
    model_parquet_path = argv[6]
    xenograft_sample_parquet_path = argv[7]

    output_path = argv[8]

    spark = SparkSession.builder.getOrCreate()
    raw_model_df = spark.read.parquet(raw_model_parquet_path)
    engraftment_site_df = spark.read.parquet(engraftment_site_parquet_path)
    engraftment_type_df = spark.read.parquet(engraftment_type_parquet_path)
    engraftment_material_df = spark.read.parquet(engraftment_material_parquet_path)
    model_df = spark.read.parquet(model_parquet_path)
    xenograft_sample_df = spark.read.parquet(xenograft_sample_parquet_path)
    host_strain_df = spark.read.parquet(host_strain_parquet_path)

    specimen_df = transform_specimen(
        raw_model_df,
        engraftment_site_df,
        engraftment_type_df,
        engraftment_material_df,
        model_df,
        xenograft_sample_df,
        host_strain_df)
    print("res trans")
    specimen_df.show()
    specimen_df.write.mode("overwrite").parquet(output_path)


def transform_specimen(
        raw_model_df: DataFrame,
        engraftment_site_df: DataFrame,
        engraftment_type_df: DataFrame,
        engraftment_material_df: DataFrame,
        model_df: DataFrame,
        xenograft_sample_df: DataFrame,
        host_strain_df: DataFrame) -> DataFrame:

    specimen_df = clean_data_before_join(raw_model_df)
    print("Init")
    specimen_df.show()
    specimen_df = add_id(specimen_df, "id")

    specimen_df = set_fk_engraftment_site(specimen_df, engraftment_site_df)
    specimen_df = set_fk_engraftment_type(specimen_df, engraftment_type_df)
    specimen_df = set_fk_engraftment_material(specimen_df, engraftment_material_df)
    specimen_df = set_fk_model(specimen_df, model_df)
    # specimen_df = set_fk_xenograft_sample(specimen_df, xenograft_sample_df)
    specimen_df = set_fk_host_strain(specimen_df, host_strain_df)

    specimen_df = get_columns_expected_order(specimen_df)

    return specimen_df


def clean_data_before_join(raw_model_df: DataFrame) -> DataFrame:
    specimen_df = raw_model_df.select(
        "model_id",
        "host_strain_nomenclature",
        "passage_number",
        "engraftment_site",
        "engraftment_type",
        "sample_type"
    )
    specimen_df = specimen_df.withColumn("external_id", lit(""))
    specimen_df = specimen_df.withColumn("engraftment_site", init_cap_and_trim_all("engraftment_site"))
    specimen_df = specimen_df.withColumn("engraftment_type", init_cap_and_trim_all("engraftment_type"))
    specimen_df = specimen_df.withColumn("sample_type", init_cap_and_trim_all("sample_type"))
    return specimen_df


def set_fk_engraftment_site(specimen_df: DataFrame, engraftment_site_df: DataFrame) -> DataFrame:
    specimen_df = transform_to_fk(
        specimen_df, engraftment_site_df, "engraftment_site", "name", "id", "engraftment_site_id")
    return specimen_df


def set_fk_engraftment_type(specimen_df: DataFrame, engraftment_type_df: DataFrame) -> DataFrame:
    specimen_df = transform_to_fk(
        specimen_df, engraftment_type_df, "engraftment_type", "name", "id", "engraftment_type_id")
    return specimen_df


def set_fk_engraftment_material(specimen_df: DataFrame, engraftment_material_df: DataFrame) -> DataFrame:
    specimen_df = transform_to_fk(
        specimen_df, engraftment_material_df, "sample_type", "name", "id", "engraftment_material_id")
    return specimen_df


def set_fk_host_strain(specimen_df: DataFrame, host_strain_df: DataFrame) -> DataFrame:
    print("specimen_df cols", specimen_df.columns)
    specimen_df.show()
    print("host_strain_df cols", host_strain_df.columns)
    host_strain_df.show()
    specimen_df = transform_to_fk(
        specimen_df, host_strain_df, "host_strain_nomenclature", "nomenclature", "id", "host_strain_id")
    print("after hs fk")
    specimen_df.show()
    return specimen_df


def set_fk_model(specimen_df: DataFrame, model_df: DataFrame) -> DataFrame:
    specimen_df = specimen_df.withColumnRenamed("model_id", "model_id_ref")
    specimen_df = transform_to_fk(specimen_df, model_df, "model_id_ref", "external_model_id", "id", "model_id")
    return specimen_df


def set_fk_xenograft_sample(specimen_df: DataFrame, xenograft_sample_df: DataFrame) -> DataFrame:
    print("specimen_df cols", specimen_df.columns)
    specimen_df.show(10)
    print("xenograft_sample_df cols", xenograft_sample_df.columns)
    xenograft_sample_df.show(10)
    specimen_df = specimen_df.withColumnRenamed("model_id", "model_id_ref")
    specimen_df = transform_to_fk(
        specimen_df, xenograft_sample_df, "model_id_ref", "xenograft_sample_id", "model_id", "model_id")
    return specimen_df


def get_columns_expected_order(specimen_df: DataFrame) -> DataFrame:
    return specimen_df.select(
        "id",
        "external_id",
        "passage_number",
        "engraftment_site_id",
        "engraftment_type_id",
        "engraftment_material_id",
        "host_strain_id",
        "model_id")


if __name__ == "__main__":
    sys.exit(main(sys.argv))
