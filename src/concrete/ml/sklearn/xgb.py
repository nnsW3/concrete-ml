"""Implements XGBoost models."""
from __future__ import annotations

import platform
import warnings
from typing import Callable, List, Optional, Union

import numpy
import xgboost.sklearn

from ..common.debugging.custom_assert import assert_true
from ..quantization import QuantizedArray
from .base import BaseTreeEstimatorMixin
from .tree_to_numpy import tree_to_numpy


# Disabling invalid-name to use uppercase X
# pylint: disable=invalid-name
class XGBClassifier(xgboost.sklearn.XGBClassifier, BaseTreeEstimatorMixin):
    """Implements the XGBoost classifier."""

    sklearn_alg = xgboost.sklearn.XGBClassifier
    q_x_byfeatures: List[QuantizedArray]
    n_bits: int
    q_y: QuantizedArray
    _tensor_tree_predict: Callable

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        n_bits: int = 7,
        max_depth: Optional[int] = 3,
        learning_rate: Optional[float] = 0.1,
        n_estimators: Optional[int] = 20,
        booster: Optional[str] = None,
        tree_method: Optional[str] = None,
        n_jobs: Optional[int] = None,
        gamma: Optional[float] = None,
        min_child_weight: Optional[float] = None,
        max_delta_step: Optional[float] = None,
        importance_type: Optional[str] = None,
        colsample_bytree: Optional[float] = None,
        colsample_bylevel: Optional[float] = None,
        colsample_bynode: Optional[float] = None,
        scale_pos_weight: Optional[float] = None,
        subsample: Optional[float] = None,
        reg_alpha: Optional[float] = None,
        reg_lambda: Optional[float] = None,
        objective: Optional[str] = "binary:logistic",
        use_label_encoder: Optional[bool] = False,
        base_score: Optional[float] = None,
        random_state: Optional[
            Union[numpy.random.RandomState, int]  # pylint: disable=no-member
        ] = None,
        verbosity: Optional[int] = None,
    ):
        """Initialize the XGBoostClassifier.

        Args:
            n_bits (int): The number of bits to use. Defaults to 7.
            max_depth (Optional[int]): The maximum depth of the tree. Defaults to 3.
            learning_rate (Optional[float]): The learning rate. Defaults to 0.1.
            n_estimators (Optional[int]): The number of estimators. Defaults to 20.
            booster (Optional[str]): The booster type to use. Defaults to None.
            tree_method (Optional[str]): The tree method to use. Defaults to None.
            n_jobs (Optional[int]): The number of jobs to use. Defaults to None.
            gamma (Optional[float]): The gamma parameter. Defaults to None.
            min_child_weight (Optional[float]): The minimum child weight. Defaults to None.
            max_delta_step (Optional[float]): The maximum delta step. Defaults to None.
            importance_type (Optional[str]): The importance type. Defaults to None.
            colsample_bytree (Optional[float]): The colsample by tree parameter. Defaults to None.
            colsample_bylevel (Optional[float]): The colsample by level parameter.
                Defaults to None.
            colsample_bynode (Optional[float]): The colsample by node parameter. Defaults to None.
            scale_pos_weight (Optional[float]): The scale pos weight parameter. Defaults to None.
            subsample (Optional[float]): The subsample parameter. Defaults to None.
            reg_alpha (Optional[float]): The regularization alpha parameter. Defaults to None.
            reg_lambda (Optional[float]): The regularization lambda parameter. Defaults to None.
            objective (Optional[str]): The objective function to use.
                Defaults to "binary:logistic".
            use_label_encoder (Optional[bool]): Whether to use the label encoder.
                Defaults to False.
            base_score (Optional[float]): The base score. Defaults to 0.5.
            random_state (Optional[Union[numpy.random.RandomState, int]]): The random state.
                Defaults to None.
            verbosity (Optional[int]): Verbosity level. Defaults to 0.
        """
        # base_score != 0.5 or None seems to not pass our tests (see #474)
        assert_true(
            base_score in [0.5, None],
            f"Currently, only 0.5 or None are supported for base_score. Got {base_score}",
        )

        # FIXME: see https://github.com/zama-ai/concrete-ml-internal/issues/503, there is currently
        # an issue with n_jobs != 1 on macOS
        # FIXME: https://github.com/zama-ai/concrete-ml-internal/issues/506, remove this workaround
        # once https://github.com/zama-ai/concrete-ml-internal/issues/503 is fixed
        if platform.system() == "Darwin":
            if n_jobs != 1:  # pragma: no cover
                warnings.warn("forcing n_jobs = 1 on mac for segfault issue")  # pragma: no cover
                n_jobs = 1  # pragma: no cover

        super().__init__(
            max_depth=max_depth,
            learning_rate=learning_rate,
            n_estimators=n_estimators,
            booster=booster,
            tree_method=tree_method,
            n_jobs=n_jobs,
            gamma=gamma,
            min_child_weight=min_child_weight,
            max_delta_step=max_delta_step,
            importance_type=importance_type,
            colsample_bytree=colsample_bytree,
            colsample_bylevel=colsample_bylevel,
            colsample_bynode=colsample_bynode,
            scale_pos_weight=scale_pos_weight,
            subsample=subsample,
            reg_alpha=reg_alpha,
            reg_lambda=reg_lambda,
            objective=objective,
            use_label_encoder=use_label_encoder,
            random_state=random_state,
            verbosity=verbosity,
            base_score=base_score,
        )
        BaseTreeEstimatorMixin.__init__(self, n_bits=n_bits)
        self.init_args = {
            "max_depth": max_depth,
            "learning_rate": learning_rate,
            "n_estimators": n_estimators,
            "booster": booster,
            "tree_method": tree_method,
            "n_jobs": n_jobs,
            "gamma": gamma,
            "min_child_weight": min_child_weight,
            "max_delta_step": max_delta_step,
            "colsample_bytree": colsample_bytree,
            "colsample_bylevel": colsample_bylevel,
            "colsample_bynode": colsample_bynode,
            "scale_pos_weight": scale_pos_weight,
            "subsample": subsample,
            "reg_alpha": reg_alpha,
            "reg_lambda": reg_lambda,
            "objective": objective,
            "use_label_encoder": use_label_encoder,
            "random_state": random_state,
            "verbosity": verbosity,
            "base_score": base_score,
        }

    # pylint: enable=too-many-arguments

    #  pylint: disable=arguments-differ
    def fit(self, X: numpy.ndarray, y: numpy.ndarray, **kwargs) -> "XGBClassifier":
        """Fit the XGBoostClassifier.

        Args:
            X (numpy.ndarray): The input data.
            y (numpy.ndarray): The target data.
            **kwargs: args for super().fit

        Returns:
            XGBoostClassifier: The XGBoostClassifier.
        """
        # mypy
        assert self.n_bits is not None

        qX = numpy.zeros_like(X)
        self.q_x_byfeatures = []

        # Quantization of each feature in X
        for i in range(X.shape[1]):
            q_x_ = QuantizedArray(n_bits=self.n_bits, values=X[:, i])
            self.q_x_byfeatures.append(q_x_)
            qX[:, i] = q_x_.qvalues.astype(numpy.int32)

        super().fit(qX, y, **kwargs)

        # Tree ensemble inference to numpy
        # Have to ignore mypy (Can't assign to a method)
        self._tensor_tree_predict, self.q_y = tree_to_numpy(  # type: ignore
            self, qX, framework="xgboost", output_n_bits=self.n_bits
        )
        return self

    def predict(
        self, X: numpy.ndarray, *args, execute_in_fhe: bool = False, **kwargs
    ) -> numpy.ndarray:
        """Predict the target values.

        Args:
            X (numpy.ndarray): The input data.
            args: args for super().predict
            execute_in_fhe (bool): Whether to execute in FHE. Defaults to False.
            kwargs: kwargs for super().predict

        Returns:
            numpy.ndarray: The predicted target values.
        """
        y_preds = self.predict_proba(X, execute_in_fhe=execute_in_fhe, *args, **kwargs)
        y_preds = numpy.argmax(y_preds, axis=1)
        return y_preds

    def predict_proba(
        self, X: numpy.ndarray, *args, execute_in_fhe: bool = False, **kwargs
    ) -> numpy.ndarray:
        """Predict the probabilities.

        Args:
            X (numpy.ndarray): The input data.
            args: args for super().predict
            execute_in_fhe (bool): Whether to execute in FHE. Defaults to False.
            kwargs: kwargs for super().predict

        Returns:
            numpy.ndarray: The predicted probabilities.
        """
        assert_true(len(args) == 0, f"Unsupported **args parameters {args}")
        assert_true(len(kwargs) == 0, f"Unsupported **kwargs parameters {kwargs}")
        assert_true(execute_in_fhe is False, "execute_in_fhe is not supported")

        qX = self.quantize_input(X)
        y_preds = self._tensor_tree_predict(qX)[0]
        y_preds = self.q_y.update_quantized_values(y_preds)
        y_preds = numpy.squeeze(y_preds)
        assert_true(y_preds.ndim > 1, "y_preds should be a 2D array")
        y_preds = numpy.transpose(y_preds)
        y_preds = numpy.sum(y_preds, axis=1, keepdims=True)
        y_preds = 1.0 / (1.0 + numpy.exp(-y_preds))
        y_preds = numpy.concatenate((1 - y_preds, y_preds), axis=1)
        return y_preds