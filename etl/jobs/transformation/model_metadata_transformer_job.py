import sys

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import lit, col, concat, concat_ws, collect_list, collect_set, when, array, size

from etl.constants import Constants
from etl.jobs.transformation.links_generation.resources_per_model_util import add_raw_data_resources


def main(argv):
    """
    Creates a parquet file with model_information + more metadata joined to it.
    Intermediate transformation used by search_index transformation.
    :param list argv: the list elements should be:
                    [1]: Parquet file path with the model_information transformed data.
                    [2]: Parquet file path with the search_index_patient_sample transformed data.
                    [3]: Parquet file path with the xenograft_model_specimen_parquet_path transformed data.
                    [4]: Parquet file path with the quality_assurance_parquet_path transformed data.
                    [5]: Parquet file path with the treatment_harmonisation_helper_parquet_path transformed data.
                    [6]: Parquet file path with the search_index_molecular_characterization_parquet_path transformed data.
                    [2]: Output file
    """
    model_parquet_path = argv[1]
    search_index_patient_sample_parquet_path = argv[2]
    xenograft_model_specimen_parquet_path = argv[3]
    quality_assurance_parquet_path = argv[4]
    treatment_harmonisation_helper_parquet_path = argv[5]
    search_index_molecular_characterization_parquet_path = argv[6]
    output_path = argv[7]

    spark = SparkSession.builder.getOrCreate()
    model_df = spark.read.parquet(model_parquet_path)
    search_index_patient_sample_df = spark.read.parquet(search_index_patient_sample_parquet_path)
    xenograft_model_specimen_df = spark.read.parquet(xenograft_model_specimen_parquet_path)
    quality_assurance_df = spark.read.parquet(quality_assurance_parquet_path)
    treatment_harmonisation_helper_df = spark.read.parquet(treatment_harmonisation_helper_parquet_path)
    search_index_molecular_char_df = spark.read.parquet(search_index_molecular_characterization_parquet_path)

    model_metadata = transform_model_metadata(
        model_df,
        search_index_patient_sample_df,
        xenograft_model_specimen_df,
        quality_assurance_df,
        treatment_harmonisation_helper_df,
        search_index_molecular_char_df
    )

    model_metadata.write.mode("overwrite").parquet(output_path)


def transform_model_metadata(
        model_df: DataFrame,
        search_index_patient_sample_df: DataFrame,
        xenograft_model_specimen_df: DataFrame,
        quality_assurance_df: DataFrame,
        treatment_harmonisation_helper_df: DataFrame,
        search_index_molecular_char_df
) -> DataFrame:
    model_df = get_formatted_model(model_df)

    # Add patient/patient sample info to the models
    model_df = model_df.join(search_index_patient_sample_df, on=["pdcm_model_id", Constants.DATA_SOURCE_COLUMN])

    # Add JSON column with all quality assurance data associated to each model
    model_df = add_quality_assurance_data(model_df, quality_assurance_df)
    # Add JSON column with all xenografts associated to each model
    model_df = add_xenograft_model_specimen_data(model_df, xenograft_model_specimen_df)

    # Adding treatment list (patient treatment) and model treatment list (model drug dosing) to search_index
    treatment_harmonisation_helper_df = treatment_harmonisation_helper_df.withColumnRenamed("model_id", "pdcm_model_id")
    model_df = model_df.join(treatment_harmonisation_helper_df, on=["pdcm_model_id"], how="left")

    # Add dataset_available column
    model_df = add_dataset_available(model_df, search_index_molecular_char_df)

    # Add raw_data_resources column
    model_df = add_raw_data_resources(model_df, search_index_molecular_char_df)

    return model_df


# Get the model information df in the expected format for other transformations
def get_formatted_model(
        model_df: DataFrame
) -> DataFrame:
    model_df.show()
    # Renaming columns
    model_df = model_df.withColumnRenamed("type", "model_type")
    model_df = model_df.withColumnRenamed("id", "pdcm_model_id")
    model_df = model_df.withColumn(Constants.DATA_SOURCE_COLUMN, col("data_source"))

    model_df = model_df.select(
        "pdcm_model_id",
        "external_model_id",
        "model_type",
        "data_source",
        "publications",
        "license_name",
        "license_url",
        Constants.DATA_SOURCE_COLUMN
    )
    return model_df


def add_quality_assurance_data(df: DataFrame, quality_assurance_df: DataFrame) -> DataFrame:
    quality_assurance_df = quality_assurance_df.withColumn(
        "json_entry",
        concat(lit("{"),
               lit("\"validation_technique\": "), lit("\""), col("validation_technique"), lit("\", "),
               lit("\"description\": "), lit("\""), col("description"), lit("\", "),
               lit("\"passages_tested\": "), lit("\""), col("passages_tested"), lit("\", "),
               lit("\"validation_host_strain_nomenclature\": "),
               lit("\""), col("validation_host_strain_nomenclature"), lit("\""),
               concat(lit("}"))))

    quality_data_per_model_df = quality_assurance_df.groupby("model_id").agg(
        concat_ws(", ", collect_list(quality_assurance_df.json_entry)).alias("quality_assurance"))
    quality_data_per_model_df = quality_data_per_model_df.withColumn(
        "quality_assurance",
        concat(lit("["), col("quality_assurance"), concat(lit("]"))))
    df = df.join(
        quality_data_per_model_df, df.pdcm_model_id == quality_data_per_model_df.model_id, how='left')
    df = df.drop("model_id")
    return df


def add_xenograft_model_specimen_data(df: DataFrame, xenograft_model_specimen_df: DataFrame) -> DataFrame:
    xenograft_model_specimen_df = xenograft_model_specimen_df.select(
        "model_id", "host_strain_name", "host_strain_nomenclature", "engraftment_site", "engraftment_type",
        "sample_type", "sample_state", "passage_number")

    xenograft_model_specimen_df = xenograft_model_specimen_df.withColumn(
        "json_entry",
        concat(lit("{"),
               lit("\"host_strain_name\": "), lit("\""), col("host_strain_name"), lit("\", "),
               lit("\"host_strain_nomenclature\": "), lit("\""), col("host_strain_nomenclature"), lit("\", "),
               lit("\"engraftment_site\": "), lit("\""), col("engraftment_site"), lit("\", "),
               lit("\"engraftment_type\": "), lit("\""), col("engraftment_type"), lit("\", "),
               lit("\"engraftment_sample_type\": "), lit("\""), col("sample_type"), lit("\", "),
               lit("\"engraftment_sample_state\": "), lit("\""), col("sample_state"), lit("\", "),
               lit("\"passage_number\": "), lit("\""), col("passage_number"), lit("\""),
               concat(lit("}"))))

    xenograft_model_specimen_per_model_df = xenograft_model_specimen_df.groupby("model_id").agg(
        concat_ws(", ", collect_list(xenograft_model_specimen_df.json_entry)).alias("xenograft_model_specimens"))
    xenograft_model_specimen_per_model_df = xenograft_model_specimen_per_model_df.withColumn(
        "xenograft_model_specimens",
        concat(lit("["), col("xenograft_model_specimens"), concat(lit("]"))))
    cond = df.pdcm_model_id == xenograft_model_specimen_per_model_df.model_id
    df = df.join(xenograft_model_specimen_per_model_df, cond, how='left')
    df = df.drop("model_id")
    return df


def add_dataset_available(df: DataFrame, search_index_molecular_char_df: DataFrame) -> DataFrame:
    model_mol_char_availability_df = search_index_molecular_char_df.groupby("model_id").agg(
        collect_set("molecular_characterisation_type").alias("dataset_available")
    )

    df = df.join(
        model_mol_char_availability_df, on=[df.pdcm_model_id == model_mol_char_availability_df.model_id], how='left')

    # Adding drug dosing and patient treatment to dataset_available
    df = df.withColumn(
        "dataset_available",
        when(
            col("model_treatment_list").isNotNull() & (size("model_treatment_list") > 0),
            when(col("dataset_available").isNotNull(),
                 concat(col("dataset_available"), array(lit("dosing studies")))).otherwise(
                array(lit("dosing studies")))
        ).otherwise(col("dataset_available"))
    )

    df = df.withColumn(
        "dataset_available",
        when(
            col("treatment_list").isNotNull() & (size("treatment_list") > 0),
            when(col("dataset_available").isNotNull(),
                 concat(col("dataset_available"), array(lit("patient treatment")))).otherwise(
                array(lit("patient treatment")))
        ).otherwise(col("dataset_available"))
    )

    # Add publication flag to dataset available
    df = df.withColumn(
        "dataset_available",
        when(
            col("publications").isNotNull(),
            when(col("dataset_available").isNotNull(),
                 concat(col("dataset_available"), array(lit("publication")))).otherwise(
                array(lit("publication")))
        ).otherwise(col("dataset_available"))
    )

    df = df.drop("model_id")

    return df


if __name__ == "__main__":
    sys.exit(main(sys.argv))
