ALTER TABLE diagnosis DROP CONSTRAINT IF EXISTS pk_diagnosis CASCADE;
ALTER TABLE ethnicity DROP CONSTRAINT IF EXISTS pk_ethnicity CASCADE;
ALTER TABLE provider_type DROP CONSTRAINT IF EXISTS pk_provider_type CASCADE;
ALTER TABLE provider_group DROP CONSTRAINT IF EXISTS pk_provider_group CASCADE;
ALTER TABLE provider_group DROP CONSTRAINT IF EXISTS pk_provider_group CASCADE;
ALTER TABLE patient DROP CONSTRAINT IF EXISTS pk_patient CASCADE;
ALTER TABLE publication_group DROP CONSTRAINT IF EXISTS pk_publication_group CASCADE;
ALTER TABLE accessibility_group DROP CONSTRAINT IF EXISTS pk_accessibility_group CASCADE;
ALTER TABLE contact_people DROP CONSTRAINT IF EXISTS pk_contact_people CASCADE;
ALTER TABLE contact_form DROP CONSTRAINT IF EXISTS pk_contact_form CASCADE;
ALTER TABLE source_database DROP CONSTRAINT IF EXISTS pk_source_database CASCADE;
ALTER TABLE model DROP CONSTRAINT IF EXISTS pk_model CASCADE;
ALTER TABLE quality_assurance DROP CONSTRAINT IF EXISTS pk_quality_assurance CASCADE;
ALTER TABLE tissue DROP CONSTRAINT IF EXISTS pk_tissue CASCADE;
ALTER TABLE tumour_type DROP CONSTRAINT IF EXISTS pk_tumour_type CASCADE;
ALTER TABLE patient_sample DROP CONSTRAINT IF EXISTS pk_patient_sample CASCADE;
ALTER TABLE xenograft_sample DROP CONSTRAINT IF EXISTS pk_xenograft_sample CASCADE;
ALTER TABLE patient_snapshot DROP CONSTRAINT IF EXISTS pk_patient_snapshot CASCADE;
ALTER TABLE engraftment_site DROP CONSTRAINT IF EXISTS pk_engraftment_site CASCADE;
ALTER TABLE engraftment_sample_state DROP CONSTRAINT IF EXISTS pk_engraftment_sample_state CASCADE;
ALTER TABLE engraftment_sample_type DROP CONSTRAINT IF EXISTS pk_engraftment_sample_type CASCADE;
ALTER TABLE engraftment_type DROP CONSTRAINT IF EXISTS pk_engraftment_type CASCADE;
ALTER TABLE host_strain DROP CONSTRAINT IF EXISTS pk_host_strain CASCADE;
ALTER TABLE project_group DROP CONSTRAINT IF EXISTS pk_project_group CASCADE;
ALTER TABLE treatment DROP CONSTRAINT IF EXISTS pk_treatment CASCADE;
ALTER TABLE response DROP CONSTRAINT IF EXISTS pk_response CASCADE;
ALTER TABLE molecular_characterization_type DROP CONSTRAINT IF EXISTS pk_molecular_characterization_type CASCADE;
ALTER TABLE platform DROP CONSTRAINT IF EXISTS pk_platform CASCADE;
ALTER TABLE molecular_characterization DROP CONSTRAINT IF EXISTS pk_molecular_characterization CASCADE;
ALTER TABLE cna_molecular_data DROP CONSTRAINT IF EXISTS pk_cna_molecular_data CASCADE;
ALTER TABLE cytogenetics_molecular_data DROP CONSTRAINT IF EXISTS pk_cytogenetics_molecular_data CASCADE;
ALTER TABLE expression_molecular_data DROP CONSTRAINT IF EXISTS pk_expression_molecular_data CASCADE;
ALTER TABLE mutation_marker DROP CONSTRAINT IF EXISTS pk_mutation_marker CASCADE;
ALTER TABLE mutation_measurement_data DROP CONSTRAINT IF EXISTS pk_mutation_measurement_data CASCADE;
ALTER TABLE specimen DROP CONSTRAINT IF EXISTS pk_specimen CASCADE;
ALTER TABLE gene_marker DROP CONSTRAINT IF EXISTS pk_gene_marker CASCADE;
ALTER TABLE ontology_term_diagnosis DROP CONSTRAINT IF EXISTS pk_ontology_term_diagnosis CASCADE;
ALTER TABLE ontology_term_treatment DROP CONSTRAINT IF EXISTS pk_ontology_term_treatment CASCADE;
ALTER TABLE ontology_term_regimen DROP CONSTRAINT IF EXISTS pk_ontology_term_regimen CASCADE;
ALTER TABLE sample_to_ontology DROP CONSTRAINT IF EXISTS pk_sample_to_ontology CASCADE;