## Week 4 — Azure Cloud Fundamentals & Data Pipeline (ADF)

**Objective:** Build an end-to-end data pipeline using Azure Storage and Azure Data Factory (ADF), covering core Azure cloud concepts.

## What was done
- Created a Resource Group (`rg-superstore-pipeline`) in Central India
- Provisioned a Storage Account and Blob Container, uploaded the Superstore sales dataset (CSV)
- Created an Azure Data Factory (V2) instance and explored the Author, Monitor, and Manage panes
- Configured a Linked Service connecting ADF to Blob Storage
- Created source and destination datasets (DelimitedText)
- Built a pipeline with:
  - **Get Metadata activity** – validates file existence, size, last modified date, and column count
  - **Copy Data activity** – copies data from source to destination blob
- Executed the pipeline via Debug; both activities succeeded
- Verified pipeline run history and metadata output via Monitor
- Configured IAM roles (Reader, Contributor) at the resource group level

### Result
End-to-end pipeline (**Blob → ADF → Blob**) with metadata validation, successfully built, executed, and monitored.
