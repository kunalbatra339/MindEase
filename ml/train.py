import os
import joblib
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from datasets import load_dataset

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.svm import LinearSVC
from sklearn.calibration import CalibratedClassifierCV
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline

from sklearn.metrics import (
    classification_report,
    f1_score,
    accuracy_score,
    confusion_matrix
)

from sklearn.model_selection import GridSearchCV


# ============================================================
# CONFIGURATION
# ============================================================

RANDOM_STATE = 42

# Emotion labels from DAIR-AI Emotion dataset
LABEL_NAMES = [
    "sadness",
    "joy",
    "love",
    "anger",
    "fear",
    "surprise"
]

# Directory containing this train.py file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Output directories
FIGURES_DIR = os.path.join(BASE_DIR, "figures")
MODELS_DIR = os.path.join(BASE_DIR, "models")

# Create directories automatically
os.makedirs(FIGURES_DIR, exist_ok=True)
os.makedirs(MODELS_DIR, exist_ok=True)


# ============================================================
# 1. LOAD AND EXPLORE DATA
# ============================================================

def load_and_explore_data():

    print("\n--- 1. Loading & Exploring Dataset ---")

    # --------------------------------------------------------
    # Load DAIR-AI Emotion dataset
    # trust_remote_code is no longer supported/required
    # --------------------------------------------------------

    dataset = load_dataset("dair-ai/emotion")

    df_train = pd.DataFrame(dataset["train"])
    df_val = pd.DataFrame(dataset["validation"])
    df_test = pd.DataFrame(dataset["test"])

    print(f"Original Training samples: {len(df_train)}")
    print(f"Original Validation samples: {len(df_val)}")
    print(f"Original Test samples: {len(df_test)}")

    # --------------------------------------------------------
    # Basic cleaning
    # --------------------------------------------------------

    for df in [df_train, df_val, df_test]:

        # Remove missing text
        df.dropna(subset=["text"], inplace=True)

        # Convert text to string
        df["text"] = df["text"].astype(str)

        # Remove empty strings
        df.drop(
            df[df["text"].str.strip() == ""].index,
            inplace=True
        )

        # Remove duplicate texts inside each split
        df.drop_duplicates(
            subset=["text"],
            inplace=True
        )

    print("\nAfter basic cleaning:")
    print(f"Training samples: {len(df_train)}")
    print(f"Validation samples: {len(df_val)}")
    print(f"Test samples: {len(df_test)}")

    # --------------------------------------------------------
    # Prevent data leakage
    #
    # If the same text exists in training and validation/test,
    # the model could effectively see the answer beforehand.
    # --------------------------------------------------------

    train_texts = set(df_train["text"])

    val_before = len(df_val)
    test_before = len(df_test)

    df_val = df_val[
        ~df_val["text"].isin(train_texts)
    ].copy()

    df_test = df_test[
        ~df_test["text"].isin(train_texts)
    ].copy()

    print("\nAfter train/validation/test leakage check:")
    print(
        f"Validation removed: "
        f"{val_before - len(df_val)} overlapping samples"
    )

    print(
        f"Test removed: "
        f"{test_before - len(df_test)} overlapping samples"
    )

    print(f"Final Training samples: {len(df_train)}")
    print(f"Final Validation samples: {len(df_val)}")
    print(f"Final Test samples: {len(df_test)}")

    # --------------------------------------------------------
    # Class distribution
    # --------------------------------------------------------

    plt.figure(figsize=(9, 6))

    sns.countplot(
        data=df_train,
        x="label"
    )

    plt.title(
        "Class Distribution in Training Set",
        fontsize=14
    )

    plt.xlabel("Emotion")
    plt.ylabel("Number of Samples")

    plt.xticks(
        ticks=range(len(LABEL_NAMES)),
        labels=LABEL_NAMES,
        rotation=20
    )

    plt.tight_layout()

    class_distribution_path = os.path.join(
        FIGURES_DIR,
        "class_distribution.png"
    )

    plt.savefig(
        class_distribution_path,
        dpi=300,
        bbox_inches="tight"
    )

    plt.close()

    print(
        f"\nSaved class distribution plot to:\n"
        f"{class_distribution_path}"
    )

    # --------------------------------------------------------
    # Print class counts
    # --------------------------------------------------------

    print("\nTraining Class Distribution:")

    class_counts = (
        df_train["label"]
        .value_counts()
        .sort_index()
    )

    for label_id, count in class_counts.items():

        emotion = (
            LABEL_NAMES[label_id]
            if label_id < len(LABEL_NAMES)
            else str(label_id)
        )

        print(
            f"{label_id} - {emotion}: {count}"
        )

    return df_train, df_val, df_test


# ============================================================
# 2. BUILD AND COMPARE BASELINE MODELS
# ============================================================

def build_and_compare_models(df_train, df_val):

    print("\n--- 2. Training Classical NLP Baselines ---")

    X_train = df_train["text"]
    y_train = df_train["label"]

    X_val = df_val["text"]
    y_val = df_val["label"]

    # --------------------------------------------------------
    # Calibrated Linear SVM
    #
    # LinearSVC itself does not provide probabilities.
    # Calibration allows predict_proba() to be used later.
    # --------------------------------------------------------

    svm_classifier = CalibratedClassifierCV(
        LinearSVC(
            class_weight="balanced",
            dual="auto",
            random_state=RANDOM_STATE
        ),
        cv=3
    )

    # --------------------------------------------------------
    # Models
    # --------------------------------------------------------

    models = {

        "Logistic Regression": Pipeline([
            (
                "tfidf",
                TfidfVectorizer(
                    max_features=10000,
                    ngram_range=(1, 2),
                    sublinear_tf=True
                )
            ),

            (
                "clf",
                LogisticRegression(
                    max_iter=1000,
                    class_weight="balanced",
                    random_state=RANDOM_STATE
                )
            )
        ]),

        "Linear SVM (Calibrated)": Pipeline([
            (
                "tfidf",
                TfidfVectorizer(
                    max_features=10000,
                    ngram_range=(1, 2),
                    sublinear_tf=True
                )
            ),

            (
                "clf",
                svm_classifier
            )
        ]),

        "Naive Bayes": Pipeline([
            (
                "tfidf",
                TfidfVectorizer(
                    max_features=10000,
                    ngram_range=(1, 2),
                    sublinear_tf=True
                )
            ),

            (
                "clf",
                MultinomialNB()
            )
        ])
    }

    # --------------------------------------------------------
    # Train and compare
    # --------------------------------------------------------

    results = []

    best_model_name = None
    best_macro_f1 = -1

    trained_models = {}

    for name, pipeline in models.items():

        print(f"\nTraining: {name}")

        pipeline.fit(
            X_train,
            y_train
        )

        preds = pipeline.predict(X_val)

        accuracy = accuracy_score(
            y_val,
            preds
        )

        macro_f1 = f1_score(
            y_val,
            preds,
            average="macro"
        )

        weighted_f1 = f1_score(
            y_val,
            preds,
            average="weighted"
        )

        results.append({
            "Model": name,
            "Accuracy": accuracy,
            "Macro F1": macro_f1,
            "Weighted F1": weighted_f1
        })

        trained_models[name] = pipeline

        print(
            f"Accuracy:     {accuracy:.4f}"
        )

        print(
            f"Macro F1:     {macro_f1:.4f}"
        )

        print(
            f"Weighted F1:  {weighted_f1:.4f}"
        )

        # Select based on Macro F1
        if macro_f1 > best_macro_f1:

            best_macro_f1 = macro_f1
            best_model_name = name

    # --------------------------------------------------------
    # Comparison table
    # --------------------------------------------------------

    comparison_df = pd.DataFrame(
        results
    ).round(4)

    print("\n--- Model Comparison ---")

    print(
        comparison_df.to_string(
            index=False
        )
    )

    print(
        f"\nBest baseline model selected: "
        f"{best_model_name}"
    )

    print(
        f"Validation Macro F1: "
        f"{best_macro_f1:.4f}"
    )

    return (
        trained_models[best_model_name],
        best_model_name
    )


# ============================================================
# 3. HYPERPARAMETER TUNING
# ============================================================

def tune_hyperparameters(
    best_pipeline,
    best_model_name,
    df_train
):

    print("\n--- 3. Hyperparameter Tuning ---")

    X_train = df_train["text"]
    y_train = df_train["label"]

    # --------------------------------------------------------
    # Logistic Regression tuning
    # --------------------------------------------------------

    if best_model_name == "Logistic Regression":

        param_grid = {

            "tfidf__min_df": [
                1,
                3
            ],

            "tfidf__ngram_range": [
                (1, 1),
                (1, 2)
            ],

            "tfidf__sublinear_tf": [
                True
            ],

            "clf__C": [
                0.1,
                1,
                10
            ]
        }

    # --------------------------------------------------------
    # Linear SVM tuning
    # --------------------------------------------------------

    elif best_model_name == "Linear SVM (Calibrated)":

        param_grid = {

            "tfidf__min_df": [
                1,
                3
            ],

            "tfidf__ngram_range": [
                (1, 1),
                (1, 2)
            ],

            "clf__estimator__C": [
                0.1,
                1,
                10
            ]
        }

    # --------------------------------------------------------
    # Naive Bayes tuning
    # --------------------------------------------------------

    elif best_model_name == "Naive Bayes":

        param_grid = {

            "tfidf__min_df": [
                1,
                3
            ],

            "tfidf__ngram_range": [
                (1, 1),
                (1, 2)
            ],

            "clf__alpha": [
                0.1,
                0.5,
                1.0
            ]
        }

    else:

        print(
            "Unknown model. Skipping tuning."
        )

        return best_pipeline

    # --------------------------------------------------------
    # Grid Search
    # --------------------------------------------------------

    print(
        "\nRunning GridSearchCV..."
    )

    print(
        "This may take a few minutes."
    )

    grid_search = GridSearchCV(

        estimator=best_pipeline,

        param_grid=param_grid,

        cv=3,

        scoring="f1_macro",

        n_jobs=-1,

        verbose=1
    )

    grid_search.fit(
        X_train,
        y_train
    )

    print(
        "\nBest parameters found:"
    )

    print(
        grid_search.best_params_
    )

    print(
        f"\nBest cross-validation "
        f"Macro F1: "
        f"{grid_search.best_score_:.4f}"
    )

    return grid_search.best_estimator_


# ============================================================
# 4. FINAL TEST EVALUATION + ERROR ANALYSIS
# ============================================================

def evaluate_and_analyze_errors(
    model,
    df_test
):

    print(
        "\n--- 4. Final Evaluation on Isolated Test Set ---"
    )

    X_test = df_test["text"]
    y_test = df_test["label"]

    # --------------------------------------------------------
    # Predictions
    # --------------------------------------------------------

    preds = model.predict(
        X_test
    )

    # --------------------------------------------------------
    # Overall metrics
    # --------------------------------------------------------

    accuracy = accuracy_score(
        y_test,
        preds
    )

    macro_f1 = f1_score(
        y_test,
        preds,
        average="macro"
    )

    weighted_f1 = f1_score(
        y_test,
        preds,
        average="weighted"
    )

    print(
        f"\nTest Accuracy: "
        f"{accuracy:.4f}"
    )

    print(
        f"Test Macro F1: "
        f"{macro_f1:.4f}"
    )

    print(
        f"Test Weighted F1: "
        f"{weighted_f1:.4f}"
    )

    # --------------------------------------------------------
    # Classification report
    # --------------------------------------------------------

    print(
        "\nClassification Report:"
    )

    print(
        classification_report(
            y_test,
            preds,
            target_names=LABEL_NAMES,
            digits=4
        )
    )

    # --------------------------------------------------------
    # Confusion Matrix
    # --------------------------------------------------------

    cm = confusion_matrix(
        y_test,
        preds
    )

    plt.figure(
        figsize=(8, 7)
    )

    sns.heatmap(
        cm,
        annot=True,
        fmt="d",
        cmap="Blues",
        xticklabels=LABEL_NAMES,
        yticklabels=LABEL_NAMES
    )

    plt.title(
        "Emotion Classification Confusion Matrix"
    )

    plt.xlabel(
        "Predicted Emotion"
    )

    plt.ylabel(
        "Actual Emotion"
    )

    plt.tight_layout()

    confusion_matrix_path = os.path.join(
        FIGURES_DIR,
        "confusion_matrix.png"
    )

    plt.savefig(
        confusion_matrix_path,
        dpi=300,
        bbox_inches="tight"
    )

    plt.close()

    print(
        f"Saved confusion matrix to:\n"
        f"{confusion_matrix_path}"
    )

    # --------------------------------------------------------
    # Error Analysis
    # --------------------------------------------------------

    print(
        "\n--- Error Analysis "
        "(Most Confident Misclassifications) ---"
    )

    # Both Logistic Regression and calibrated SVM and NB
    # provide predict_proba()
    probs = model.predict_proba(
        X_test
    )

    errors = []

    for text, actual, pred, prob in zip(
        X_test,
        y_test,
        preds,
        probs
    ):

        if actual != pred:

            confidence = prob[pred]

            errors.append(
                (
                    text,
                    LABEL_NAMES[actual],
                    LABEL_NAMES[pred],
                    confidence
                )
            )

    # Highest confidence incorrect predictions first
    errors.sort(
        key=lambda x: x[3],
        reverse=True
    )

    if not errors:

        print(
            "No misclassifications found."
        )

    else:

        for (
            text,
            actual,
            pred,
            confidence
        ) in errors[:10]:

            print(
                f"\nText: \"{text}\""
            )

            print(
                f"Actual: {actual}"
            )

            print(
                f"Predicted: {pred}"
            )

            print(
                f"Confidence: "
                f"{confidence:.4f}"
            )

    return {
        "accuracy": accuracy,
        "macro_f1": macro_f1,
        "weighted_f1": weighted_f1
    }


# ============================================================
# 5. SAVE MODEL
# ============================================================

def save_model(
    model,
    filepath=None
):

    print(
        "\n--- 5. Saving Final Model ---"
    )

    if filepath is None:

        filepath = os.path.join(
            MODELS_DIR,
            "emotion_model.pkl"
        )

    # Make sure directory exists
    os.makedirs(
        os.path.dirname(filepath),
        exist_ok=True
    )

    # Save complete pipeline
    joblib.dump(
        model,
        filepath
    )

    print(
        f"\nModel successfully saved to:"
    )

    print(
        filepath
    )

    print(
        "\nThe saved .pkl file contains:"
    )

    print(
        "  - TF-IDF text preprocessing"
    )

    print(
        "  - Trained emotion classifier"
    )

    print(
        "  - Complete prediction pipeline"
    )


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    print(
        "\n"
        "=" * 60
    )

    print(
        "MindEase Emotion Classification Training"
    )

    print(
        "=" * 60
    )

    # --------------------------------------------------------
    # STEP 1: Load and clean dataset
    # --------------------------------------------------------

    df_train, df_val, df_test = (
        load_and_explore_data()
    )

    # --------------------------------------------------------
    # STEP 2: Compare baseline models
    # --------------------------------------------------------

    best_baseline, best_model_name = (
        build_and_compare_models(
            df_train,
            df_val
        )
    )

    # --------------------------------------------------------
    # STEP 3: Tune winning model
    # --------------------------------------------------------

    final_model = tune_hyperparameters(
        best_baseline,
        best_model_name,
        df_train
    )

    # --------------------------------------------------------
    # STEP 4: Final evaluation on untouched test set
    # --------------------------------------------------------

    metrics = evaluate_and_analyze_errors(
        final_model,
        df_test
    )

    # --------------------------------------------------------
    # STEP 5: Save model
    # --------------------------------------------------------

    save_model(
        final_model
    )

    # --------------------------------------------------------
    # FINAL SUMMARY
    # --------------------------------------------------------

    print(
        "\n"
        "=" * 60
    )

    print(
        "TRAINING COMPLETE"
    )

    print(
        "=" * 60
    )

    print(
        f"Best Model: {best_model_name}"
    )

    print(
        f"Test Accuracy: "
        f"{metrics['accuracy']:.4f}"
    )

    print(
        f"Test Macro F1: "
        f"{metrics['macro_f1']:.4f}"
    )

    print(
        f"Test Weighted F1: "
        f"{metrics['weighted_f1']:.4f}"
    )

    print(
        "\nModel location:"
    )

    print(
        os.path.join(
            MODELS_DIR,
            "emotion_model.pkl"
        )
    )

    print(
        "\nTraining pipeline finished successfully."
    )