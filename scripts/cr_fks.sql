ALTER TABLE provider_group
    ADD CONSTRAINT fk_provider_group_provider_type
    FOREIGN KEY (provider_type_id)
    REFERENCES provider_type (id);

ALTER TABLE patient
    ADD CONSTRAINT fk_patient_diagnosis
    FOREIGN KEY (initial_diagnosis_id)
    REFERENCES diagnosis (id);

ALTER TABLE patient
    ADD CONSTRAINT fk_patient_provider_group
    FOREIGN KEY (provider_group_id)
    REFERENCES provider_group (id);

ALTER TABLE model
    ADD CONSTRAINT fk_model_publication_group
    FOREIGN KEY (publication_group_id)
    REFERENCES publication_group (id);

ALTER TABLE model
    ADD CONSTRAINT fk_model_accessibility_group
    FOREIGN KEY (accessibility_group_id)
    REFERENCES accessibility_group (id);

ALTER TABLE model
    ADD CONSTRAINT fk_model_contact_people
    FOREIGN KEY (contact_people_id)
    REFERENCES contact_people (id);

ALTER TABLE model
    ADD CONSTRAINT fk_model_contact_form
    FOREIGN KEY (contact_form_id)
    REFERENCES contact_form (id);

ALTER TABLE model
    ADD CONSTRAINT fk_model_source_database
    FOREIGN KEY (source_database_id)
    REFERENCES source_database (id);

ALTER TABLE quality_assurance
    ADD CONSTRAINT fk_quality_assurance_model
    FOREIGN KEY (model_id)
    REFERENCES model (id);

ALTER TABLE patient_sample
    ADD CONSTRAINT fk_patient_sample_diagnosis
    FOREIGN KEY (diagnosis_id)
    REFERENCES diagnosis (id);

ALTER TABLE patient_sample
    ADD CONSTRAINT fk_patient_primary_site
    FOREIGN KEY (primary_site_id)
    REFERENCES tissue (id);

ALTER TABLE patient_sample
    ADD CONSTRAINT fk_patient_collection_site
    FOREIGN KEY (collection_site_id)
    REFERENCES tissue (id);

ALTER TABLE patient_sample
    ADD CONSTRAINT fk_patient_sample_tumour_type
    FOREIGN KEY (tumour_type_id)
    REFERENCES tumour_type (id);

ALTER TABLE patient_sample
    ADD CONSTRAINT fk_patient_sample_model
    FOREIGN KEY (model_id)
    REFERENCES model (id);

ALTER TABLE patient_snapshot
    ADD CONSTRAINT fk_patient_snapshot_patient
    FOREIGN KEY (patient_id)
    REFERENCES patient (id);

ALTER TABLE patient_snapshot
    ADD CONSTRAINT fk_patient_snapshot_patient_sample
    FOREIGN KEY (sample_id)
    REFERENCES patient_sample (id);

ALTER TABLE platform
    ADD CONSTRAINT fk_platform_provider_group
    FOREIGN KEY (provider_group_id)
    REFERENCES provider_group (id);

ALTER TABLE molecular_characterization
    ADD CONSTRAINT fk_molecular_characterization_mchar_type
    FOREIGN KEY (molecular_characterization_type_id)
    REFERENCES molecular_characterization_type (id);

ALTER TABLE molecular_characterization
    ADD CONSTRAINT fk_molecular_characterization_platform
    FOREIGN KEY (platform_id)
    REFERENCES platform (id);

ALTER TABLE molecular_characterization
    ADD CONSTRAINT fk_molecular_characterization_patient_sample
    FOREIGN KEY (patient_sample_id)
    REFERENCES patient_sample (id);

ALTER TABLE molecular_characterization
    ADD CONSTRAINT fk_molecular_characterization_xenograft_sample
    FOREIGN KEY (xenograft_sample_id)
    REFERENCES xenograft_sample (id);

ALTER TABLE cna_molecular_data
    ADD CONSTRAINT fk_cna_molecular_data_mol_char
    FOREIGN KEY (molecular_characterization_id)
    REFERENCES molecular_characterization (id);

ALTER TABLE cytogenetics_molecular_data
    ADD CONSTRAINT fk_cytogenetics_molecular_data_mol_char
    FOREIGN KEY (molecular_characterization_id)
    REFERENCES molecular_characterization (id);

ALTER TABLE expression_molecular_data
    ADD CONSTRAINT fk_expression_molecular_data_mol_char
    FOREIGN KEY (molecular_characterization_id)
    REFERENCES molecular_characterization (id);

ALTER TABLE mutation_measurement_data
    ADD CONSTRAINT fk_mutation_measurement_data_mutation_marker
    FOREIGN KEY (mutation_marker_id)
    REFERENCES mutation_marker (id);

ALTER TABLE mutation_measurement_data
    ADD CONSTRAINT fk_mutation_measurement_data_mol_char
    FOREIGN KEY (molecular_characterization_id)
    REFERENCES molecular_characterization (id);