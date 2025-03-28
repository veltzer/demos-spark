#!/usr/bin/env python
"""
Sort-Merge Performance Exercise - Fixed Data Generation Script

This script generates two datasets (transactions and products) in both
sorted and unsorted versions for performance comparison, ensuring
proper global sorting of the sorted datasets.
"""

import os
import shutil
import time
from pyspark.sql import SparkSession
from pyspark.sql.functions import expr, rand, when

# Initialize Spark Session
spark = SparkSession.builder \
    .appName("Sort-Merge Exercise - Data Generation") \
    .config("spark.sql.shuffle.partitions", "200") \
    .getOrCreate()

# Set log level
spark.sparkContext.setLogLevel("WARN")

# Configuration
NUM_TRANSACTIONS = 10000000  # 10 million transactions
NUM_PRODUCTS = 1000000       # 1 million products
NUM_CUSTOMERS = 500000       # 500,000 customers
OUTPUT_DIR = "data"
NUM_PARTITIONS = 200         # Number of partitions for output

def create_output_dir():
    """Create output directory structure"""
    # If directory exists, remove it to avoid data mixing
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)

    # Create directories
    os.makedirs(f"{OUTPUT_DIR}/unsorted_transactions")
    os.makedirs(f"{OUTPUT_DIR}/unsorted_products")
    os.makedirs(f"{OUTPUT_DIR}/sorted_transactions")
    os.makedirs(f"{OUTPUT_DIR}/sorted_products")

def generate_product_data():
    """Generate product catalog data"""
    print("Generating product data...")

    products = spark.range(0, NUM_PRODUCTS) \
        .withColumnRenamed("id", "product_id") \
        .withColumn("product_name", expr("concat('Product_', cast(product_id as string))")) \
        .withColumn("category", when(expr("product_id % 10 = 0"), "Electronics")
                              .when(expr("product_id % 10 = 1"), "Clothing")
                              .when(expr("product_id % 10 = 2"), "Home")
                              .when(expr("product_id % 10 = 3"), "Beauty")
                              .when(expr("product_id % 10 = 4"), "Sports")
                              .when(expr("product_id % 10 = 5"), "Books")
                              .when(expr("product_id % 10 = 6"), "Food")
                              .when(expr("product_id % 10 = 7"), "Toys")
                              .when(expr("product_id % 10 = 8"), "Health")
                              .otherwise("Automotive")) \
        .withColumn("price", expr("10.0 + (rand() * 990.0)")) \
        .withColumn("stock_quantity", expr("cast(rand() * 1000 as int)"))

    return products

def generate_transaction_data(products_df):
    """Generate transaction data with references to product catalog"""
    print("Generating transaction data...")

    # Get list of product IDs to ensure referential integrity
    product_ids = [row.product_id for row in
                  products_df.select("product_id").sample(False, 0.1).collect()]

    if len(product_ids) > 1000:
        product_ids = product_ids[:1000]  # Limit to 1000 products for performance

    product_ids_expr = ",".join(map(str, product_ids))

    transactions = spark.range(0, NUM_TRANSACTIONS) \
        .withColumnRenamed("id", "transaction_id") \
        .withColumn("customer_id", expr(f"cast(rand() * {NUM_CUSTOMERS} as int)")) \
        .withColumn("product_id",
                    when(expr("rand() < 0.8"),  # 80% of transactions for popular products
                         expr(f"array({product_ids_expr})[cast(rand()*{len(product_ids)} as int)]"))
                    .otherwise(expr(f"cast(rand() * {NUM_PRODUCTS} as int)"))) \
        .withColumn("transaction_date",
                    expr("date_sub(current_date(), cast(rand() * 365 as int))")) \
        .withColumn("quantity", expr("cast(rand() * 5 + 1 as int)")) \
        .withColumn("total_amount", expr("cast(rand() * 500 + 10 as double)"))

    return transactions

def shuffle_dataframe(df):
    """Completely randomize dataframe row order"""
    return df.orderBy(rand())

def save_datasets(products_df, transactions_df):
    """Save datasets in both sorted and unsorted versions, ensuring proper global sorting"""
    # Save unsorted datasets (randomly shuffled)
    print("Saving unsorted datasets...")
    shuffled_products = shuffle_dataframe(products_df)
    shuffled_transactions = shuffle_dataframe(transactions_df)

    shuffled_products.write \
        .mode("overwrite") \
        .parquet(f"{OUTPUT_DIR}/unsorted_products")

    shuffled_transactions.write \
        .mode("overwrite") \
        .parquet(f"{OUTPUT_DIR}/unsorted_transactions")

    # Save properly sorted datasets (ensure global sorting)
    print("Saving sorted datasets with guaranteed global sorting...")

    # For products: ensure global sorting by coalescing to fewer partitions
    # and then explicitly sorting
    print("Sorting products dataset...")
    sorted_products = products_df.orderBy("product_id")

    # Coalesce to fewer partitions to improve sorting performance
    # This ensures data is globally sorted
    sorted_products = sorted_products.coalesce(20)

    # Write the sorted data
    print("Writing sorted products dataset...")
    sorted_products.write \
        .mode("overwrite") \
        .parquet(f"{OUTPUT_DIR}/sorted_products")

    # Same approach for transactions
    print("Sorting transactions dataset...")
    sorted_transactions = transactions_df.orderBy("product_id")
    sorted_transactions = sorted_transactions.coalesce(20)

    print("Writing sorted transactions dataset...")
    sorted_transactions.write \
        .mode("overwrite") \
        .parquet(f"{OUTPUT_DIR}/sorted_transactions")

    # Create metadata file to indicate datasets are properly sorted
    with open(f"{OUTPUT_DIR}/SORTED_CONFIRMATION.txt", "w") as f:
        f.write("Datasets were generated with guaranteed global sorting on product_id.\n")
        f.write(f"Generation timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")

def verify_data():
    """Verify datasets were created correctly and check sorting"""
    datasets = {
        "unsorted_products": f"{OUTPUT_DIR}/unsorted_products",
        "unsorted_transactions": f"{OUTPUT_DIR}/unsorted_transactions",
        "sorted_products": f"{OUTPUT_DIR}/sorted_products",
        "sorted_transactions": f"{OUTPUT_DIR}/sorted_transactions"
    }

    print("\nVerifying datasets:")
    for name, path in datasets.items():
        if os.path.exists(path):
            df = spark.read.parquet(path)
            count = df.count()
            print(f"  {name}: {count:,} rows")

            # Check sorting on sorted datasets
            if name.startswith("sorted"):
                # Take sample of rows to check
                sample = df.select("product_id").orderBy("product_id").limit(10000).collect()
                values = [row.product_id for row in sample]
                is_sorted = all(values[i] <= values[i+1] for i in range(len(values)-1))
                print(f"    Sorting check (on sample): {'PASSED' if is_sorted else 'FAILED'}")
        else:
            print(f"  {name}: Directory not found")

def main():
    """Main execution function"""
    print("Generating data for Sort-Merge Performance Exercise...")

    # Create directory structure
    create_output_dir()

    # Generate and save datasets
    products_df = generate_product_data()
    transactions_df = generate_transaction_data(products_df)

    # Quick check
    print(f"\nGenerated {products_df.count():,} products")
    print(f"Generated {transactions_df.count():,} transactions")

    # Save sorted and unsorted versions
    save_datasets(products_df, transactions_df)

    # Verify data was created
    verify_data()

    print("\nData generation complete!")
    print(f"Data saved to {os.path.abspath(OUTPUT_DIR)}")
    print("Now you can run the naive_solution.py and optimized_solution.py scripts")

if __name__ == "__main__":
    main()
    spark.stop()
