cd sp500_to_csv

zip -r lambda_function.zip .

aws s3 cp lambda_function.zip s3://gurrastav/sp500/

rm -rf lambda_function.zip

latest_s3_version=$(aws s3api list-object-versions --bucket gurrastav --prefix sp500/lambda_function.zip --query 'Versions[?IsLatest].[VersionId]' --output text)

aws lambda update-function-code --function-name sp500_to_csv \
    --s3-bucket gurrastav \
    --s3-key sp500/lambda_function.zip \
    --s3-object-version $latest_s3_version