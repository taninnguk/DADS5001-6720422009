import kagglehub

# Download latest version
path = kagglehub.dataset_download("starbucks/store-locations")

print("Path to dataset files:", path)