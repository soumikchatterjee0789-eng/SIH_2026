import pandas as pd


# ==========================================
# TRANSACTION CATEGORIZATION
# ==========================================

def categorize_transaction(description, transaction_type):

    text = str(description).lower()
    transaction_type = str(transaction_type).lower()


    # ======================================
    # INCOME CATEGORIES
    # ======================================

    if transaction_type == "income":

        if "salary" in text:
            return "Salary"

        if "scholarship" in text:
            return "Scholarship"

        if "freelance" in text:
            return "Freelance"

        if "business" in text:
            return "Business Income"

        return "Other Income"


    # ======================================
    # EXPENSE CATEGORIES
    # ======================================

    expense_categories = {

        "Food": [
            "swiggy",
            "zomato",
            "restaurant",
            "cafe",
            "food"
        ],

        "Transport": [
            "uber",
            "ola",
            "metro",
            "bus",
            "train",
            "fuel",
            "petrol"
        ],

        "Education": [
            "college",
            "university",
            "course",
            "book",
            "education",
            "fee"
        ],

        "Housing": [
            "hostel",
            "rent",
            "housing"
        ],

        "Shopping": [
            "amazon",
            "flipkart",
            "shopping"
        ],

        "Entertainment": [
            "netflix",
            "spotify",
            "movie",
            "gaming"
        ],

        "Health": [
            "hospital",
            "doctor",
            "pharmacy",
            "medicine"
        ]
    }


    # Check expense keywords

    for category, keywords in expense_categories.items():

        for keyword in keywords:

            if keyword in text:

                return category


    # If nothing matches

    return "Other Expense"



# ==========================================
# CSV PROCESSING
# ==========================================

def process_csv(file_path):

    # --------------------------------------
    # STEP 1: Read CSV
    # --------------------------------------

    df = pd.read_csv(file_path)


    # --------------------------------------
    # STEP 2: Required columns
    # --------------------------------------

    required_columns = [
        "date",
        "description",
        "amount",
        "type"
    ]


    # --------------------------------------
    # STEP 3: Check columns
    # --------------------------------------

    for column in required_columns:

        if column not in df.columns:

            raise ValueError(
                f"Missing required column: {column}"
            )


    # --------------------------------------
    # STEP 4: Categorize every transaction
    # --------------------------------------

    df["category"] = df.apply(

        lambda row: categorize_transaction(

            row["description"],

            row["type"]

        ),

        axis=1

    )


    # --------------------------------------
    # STEP 5: Return processed data
    # --------------------------------------

    return df