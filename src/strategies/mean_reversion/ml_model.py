#!/usr/bin/env python3
# -------------------------------------------------------------------------------------------------
#  Copyright (C) 2015-2023 Nautech Systems Pty Ltd. All rights reserved.
#  https://nautechsystems.io
#
#  Licensed under the GNU Lesser General Public License Version 3.0 (the "License");
#  You may not use this file except in compliance with the License.
#  You may obtain a copy of the License at https://www.gnu.org/licenses/lgpl-3.0.en.html
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
# -------------------------------------------------------------------------------------------------

"""
Machine learning models for the Mean Reversion strategy.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple, Union, Any
import numpy as np
import pandas as pd

# Import scikit-learn models
try:
    from sklearn.linear_model import LogisticRegression
    from sklearn.tree import DecisionTreeClassifier
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
except ImportError:
    raise ImportError(
        "scikit-learn is not installed. Please install it with: pip install scikit-learn"
    )


class BaseModel(ABC):
    """
    Base class for machine learning models.

    This abstract class defines the interface for all ML models used in the
    Mean Reversion strategy.
    """

    def __init__(self, confidence_threshold: float = 0.6):
        """
        Initialize the base model.

        Parameters
        ----------
        confidence_threshold : float
            The confidence threshold for predictions (default: 0.6).
        """
        self.confidence_threshold = confidence_threshold
        self.model = None
        self.scaler = StandardScaler()
        self.is_trained = False
        self.feature_names = []

    @abstractmethod
    def train(self, features: np.ndarray, labels: np.ndarray) -> Dict[str, float]:
        """
        Train the model.

        Parameters
        ----------
        features : np.ndarray
            The feature matrix.
        labels : np.ndarray
            The target labels.

        Returns
        -------
        Dict[str, float]
            Dictionary with training metrics.
        """
        pass

    @abstractmethod
    def predict(self, features: np.ndarray) -> Tuple[int, float]:
        """
        Make a prediction.

        Parameters
        ----------
        features : np.ndarray
            The feature vector.

        Returns
        -------
        Tuple[int, float]
            The predicted class and confidence.
        """
        pass

    def preprocess_features(self, features: np.ndarray) -> np.ndarray:
        """
        Preprocess features before prediction.

        Parameters
        ----------
        features : np.ndarray
            The raw feature vector or matrix.

        Returns
        -------
        np.ndarray
            The preprocessed features.
        """
        # Ensure features is 2D
        if features.ndim == 1:
            features = features.reshape(1, -1)
        
        # Scale features if model is trained
        if self.is_trained:
            return self.scaler.transform(features)
        else:
            return features


class LogisticRegressionModel(BaseModel):
    """
    Logistic Regression model for trend prediction.
    """

    def __init__(
        self, 
        confidence_threshold: float = 0.6,
        C: float = 1.0,
        max_iter: int = 1000,
        random_state: int = 42,
    ):
        """
        Initialize the Logistic Regression model.

        Parameters
        ----------
        confidence_threshold : float
            The confidence threshold for predictions (default: 0.6).
        C : float
            Inverse of regularization strength (default: 1.0).
        max_iter : int
            Maximum number of iterations (default: 1000).
        random_state : int
            Random state for reproducibility (default: 42).
        """
        super().__init__(confidence_threshold)
        self.model = LogisticRegression(
            C=C,
            max_iter=max_iter,
            random_state=random_state,
        )

    def train(self, features: np.ndarray, labels: np.ndarray) -> Dict[str, float]:
        """
        Train the Logistic Regression model.

        Parameters
        ----------
        features : np.ndarray
            The feature matrix.
        labels : np.ndarray
            The target labels.

        Returns
        -------
        Dict[str, float]
            Dictionary with training metrics.
        """
        # Scale features
        X_scaled = self.scaler.fit_transform(features)
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X_scaled, labels, test_size=0.2, random_state=42
        )
        
        # Train model
        self.model.fit(X_train, y_train)
        self.is_trained = True
        
        # Evaluate model
        y_pred = self.model.predict(X_test)
        
        # Calculate metrics
        metrics = {
            "accuracy": accuracy_score(y_test, y_pred),
            "precision": precision_score(y_test, y_pred, zero_division=0),
            "recall": recall_score(y_test, y_pred, zero_division=0),
            "f1": f1_score(y_test, y_pred, zero_division=0),
        }
        
        return metrics

    def predict(self, features: np.ndarray) -> Tuple[int, float]:
        """
        Make a prediction with the Logistic Regression model.

        Parameters
        ----------
        features : np.ndarray
            The feature vector.

        Returns
        -------
        Tuple[int, float]
            The predicted class and confidence.
        """
        if not self.is_trained:
            raise ValueError("Model is not trained yet")
        
        # Preprocess features
        X_scaled = self.preprocess_features(features)
        
        # Get prediction and probability
        prediction = self.model.predict(X_scaled)[0]
        probabilities = self.model.predict_proba(X_scaled)[0]
        confidence = probabilities[prediction]
        
        return prediction, confidence


class DecisionTreeModel(BaseModel):
    """
    Decision Tree model for trend prediction.
    """

    def __init__(
        self, 
        confidence_threshold: float = 0.6,
        max_depth: int = 5,
        min_samples_split: int = 2,
        random_state: int = 42,
    ):
        """
        Initialize the Decision Tree model.

        Parameters
        ----------
        confidence_threshold : float
            The confidence threshold for predictions (default: 0.6).
        max_depth : int
            Maximum depth of the tree (default: 5).
        min_samples_split : int
            Minimum samples required to split a node (default: 2).
        random_state : int
            Random state for reproducibility (default: 42).
        """
        super().__init__(confidence_threshold)
        self.model = DecisionTreeClassifier(
            max_depth=max_depth,
            min_samples_split=min_samples_split,
            random_state=random_state,
        )

    def train(self, features: np.ndarray, labels: np.ndarray) -> Dict[str, float]:
        """
        Train the Decision Tree model.

        Parameters
        ----------
        features : np.ndarray
            The feature matrix.
        labels : np.ndarray
            The target labels.

        Returns
        -------
        Dict[str, float]
            Dictionary with training metrics.
        """
        # Scale features
        X_scaled = self.scaler.fit_transform(features)
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X_scaled, labels, test_size=0.2, random_state=42
        )
        
        # Train model
        self.model.fit(X_train, y_train)
        self.is_trained = True
        
        # Evaluate model
        y_pred = self.model.predict(X_test)
        
        # Calculate metrics
        metrics = {
            "accuracy": accuracy_score(y_test, y_pred),
            "precision": precision_score(y_test, y_pred, zero_division=0),
            "recall": recall_score(y_test, y_pred, zero_division=0),
            "f1": f1_score(y_test, y_pred, zero_division=0),
        }
        
        return metrics

    def predict(self, features: np.ndarray) -> Tuple[int, float]:
        """
        Make a prediction with the Decision Tree model.

        Parameters
        ----------
        features : np.ndarray
            The feature vector.

        Returns
        -------
        Tuple[int, float]
            The predicted class and confidence.
        """
        if not self.is_trained:
            raise ValueError("Model is not trained yet")
        
        # Preprocess features
        X_scaled = self.preprocess_features(features)
        
        # Get prediction and probability
        prediction = self.model.predict(X_scaled)[0]
        probabilities = self.model.predict_proba(X_scaled)[0]
        confidence = probabilities[prediction]
        
        return prediction, confidence
