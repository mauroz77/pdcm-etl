# Folder (host), relative to `docker-pipeline` directory, where the Excel files will be put (under {provider} folder).
INPUT_DIR = "input"

# Folder (host), relative to `docker-pipeline` directory, where all files produced by the pipeline are stored.
OUTPUT_DIR = "output"

# Folder (host), relative to `docker-pipeline/{OUTPUT_DIR}` directory, where all the data required by the ETL is stored.
# It will me mapped to the input folder in the ETL container
HOST_ETL_INPUT_DIR = "etl_input_files"

# Folder (host), relative to `docker-pipeline/{OUTPUT_DIR}` directory, where the templates (tsv files) will be copied.
TEMPLATES_DIR = HOST_ETL_INPUT_DIR + "/" + "/data/UPDOG"

# Folder (host), relative to `docker-pipeline/{OUTPUT_DIR}` directory, where the ETL will store the parquet files and intermediate files required for
# the processing. It will me mapped to the output folder in the ETL container
HOST_ETL_OUTPUT_DIR = "etl_output"

# Folder (host), relative to `docker-pipeline` directory, where the luigi conf file will be created.
CONFIG_DIR = "config"

# Folder (host), relative to `docker-pipeline/{OUTPUT_DIR}` directory, where the data related to the BioStudies submmission will be stored.
BIOSTUDIES_DIR = "biostudies"

# Folder (host), relative to `docker-pipeline/{OUTPUT_DIR}/{BIOSTUDIES_DIR}` directory, where the submission files will be generated.
SUBMISSION_DATA_DIR = "submission_data"
