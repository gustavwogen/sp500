poetry export --without-hashes --format=requirements.txt > requirements.txt

rm -rf python
mkdir python
cd python

echo "*" >> .gitignore

python3.10 -m pip install -r ../requirements.txt -t . --platform manylinux2014_x86_64 --only-binary=:all:

# remove unnecessary files
rm -rf *.dist-info
find . -name "tests" -type d | xargs -I{} rm -rf {}
find . -name "docs" -type d | xargs -I{} rm -rf {}
find . -name "__pycache__" -type d | xargs -I{} rm -rf {}
rm -rf boto*

cd ..
rm python.zip

echo "Starting zipping"
zip -r python.zip python -q
echo "Completed zipping"

echo "Attempting upload to S3"
aws s3 cp python.zip s3://gurrastav/sp500/
echo "Upload complete"

latest_s3_version=$(aws s3api list-object-versions --bucket gurrastav --prefix sp500/python.zip --query 'Versions[?IsLatest].[VersionId]' --output text)

echo "publish-layer-version"
aws lambda publish-layer-version \
    --layer-name sp500_to_csv \
    --content S3Bucket=gurrastav,S3Key=sp500/python.zip,S3ObjectVersion=$latest_s3_version \
    --compatible-runtimes python3.10 \
    --compatible-architectures x86_64


latest_layer_version=$(aws lambda list-layer-versions --layer-name sp500_to_csv --query 'LayerVersions[0].LayerVersionArn' --output text)

echo "update-function-config"
aws lambda update-function-configuration --function-name sp500_to_csv \
    --layers $latest_layer_version
