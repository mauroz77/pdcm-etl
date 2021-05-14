import luigi
from luigi.contrib.spark import SparkSubmitTask

from etl.constants import Constants
from etl.jobs.load.database_manager import copy_all_tsv_to_database
from etl.workflow.transformer import TransformPatient, TransformDiagnosis, TransformEthnicity, TransformProviderType, \
    TransformProviderGroup, TransformModel, TransformPublicationGroup, TransformTissue


class ParquetToTsv(SparkSubmitTask):
    data_dir = luigi.Parameter()
    providers = luigi.ListParameter()
    data_dir_out = luigi.Parameter()
    name = luigi.Parameter()

    app = 'etl/jobs/util/parquet_to_tsv_converter.py'

    def requires(self):
        if Constants.DIAGNOSIS_ENTITY == self.name:
            return TransformDiagnosis(self.data_dir, self.providers, self.data_dir_out)
        elif Constants.ETHNICITY_ENTITY == self.name:
            return TransformEthnicity(self.data_dir, self.providers, self.data_dir_out)
        elif Constants.PATIENT_ENTITY == self.name:
            return TransformPatient(self.data_dir, self.providers, self.data_dir_out)
        elif Constants.PROVIDER_TYPE_ENTITY == self.name:
            return TransformProviderType(self.data_dir, self.providers, self.data_dir_out)
        elif Constants.PROVIDER_GROUP_ENTITY == self.name:
            return TransformProviderGroup(self.data_dir, self.providers, self.data_dir_out)
        elif Constants.PUBLICATION_GROUP_ENTITY == self.name:
            return TransformPublicationGroup(self.data_dir, self.providers, self.data_dir_out)
        elif Constants.MODEL_ENTITY == self.name:
            return TransformModel(self.data_dir, self.providers, self.data_dir_out)
        elif Constants.TISSUE_ENTITY == self.name:
            return TransformTissue(self.data_dir, self.providers, self.data_dir_out)

    def app_options(self):
        return [
            self.input().path,
            self.output().path
        ]

    def output(self):
        return luigi.LocalTarget("{0}/{1}/{2}".format(self.data_dir_out, Constants.DATABASE_FORMATTED, self.name))


class Load(luigi.Task):
    data_dir = luigi.Parameter()
    providers = luigi.ListParameter()
    data_dir_out = luigi.Parameter()

    def requires(self):
        return [
            ParquetToTsv(self.data_dir, self.providers, self.data_dir_out, Constants.DIAGNOSIS_ENTITY),
            ParquetToTsv(self.data_dir, self.providers, self.data_dir_out, Constants.ETHNICITY_ENTITY),
            ParquetToTsv(self.data_dir, self.providers, self.data_dir_out, Constants.PATIENT_ENTITY),
            ParquetToTsv(self.data_dir, self.providers, self.data_dir_out, Constants.PROVIDER_TYPE_ENTITY),
            ParquetToTsv(self.data_dir, self.providers, self.data_dir_out, Constants.PROVIDER_GROUP_ENTITY),
            ParquetToTsv(self.data_dir, self.providers, self.data_dir_out, Constants.PUBLICATION_GROUP_ENTITY),
            ParquetToTsv(self.data_dir, self.providers, self.data_dir_out, Constants.MODEL_ENTITY),
            ParquetToTsv(self.data_dir, self.providers, self.data_dir_out, Constants.TISSUE_ENTITY)
        ]

    def run(self):
        copy_all_tsv_to_database(self.data_dir_out)
        with self.output().open('w') as out_file:
            out_file.write("data loaded")

    def output(self):
        return luigi.LocalTarget("{0}/log.txt".format(self.data_dir_out))


if __name__ == "__main__":
    luigi.run()
