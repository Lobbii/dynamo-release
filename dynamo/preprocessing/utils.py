import numpy as np
from scipy.sparse import issparse
from functools import reduce
# implmentation of Cooks' distance (but this is for Poisson distribution fitting)

# https://stackoverflow.com/questions/47686227/poisson-regression-in-statsmodels-and-r

# from __future__ import division, print_function

# https://stats.stackexchange.com/questions/356053/the-identity-link-function-does-not-respect-the-domain-of-the-gamma-family
def _weight_matrix(fitted_model):
    """Calculates weight matrix in Poisson regression

    Parameters
    ----------
    fitted_model : statsmodel object
        Fitted Poisson model

    Returns
    -------
    W : 2d array-like
        Diagonal weight matrix in Poisson regression
    """
    return np.diag(fitted_model.fittedvalues)


def _hessian(X, W):
    """Hessian matrix calculated as -X'*W*X

    Parameters
    ----------
    X : 2d array-like
        Matrix of covariates

    W : 2d array-like
        Weight matrix

    Returns
    -------
    hessian : 2d array-like
        Hessian matrix
    """
    return -np.dot(X.T, np.dot(W, X))


def _hat_matrix(X, W):
    """Calculate hat matrix = W^(1/2) * X * (X'*W*X)^(-1) * X'*W^(1/2)

    Parameters
    ----------
    X : 2d array-like
        Matrix of covariates

    W : 2d array-like
        Diagonal weight matrix

    Returns
    -------
    hat : 2d array-like
        Hat matrix
    """
    # W^(1/2)
    Wsqrt = W ** (0.5)

    # (X'*W*X)^(-1)
    XtWX = -_hessian(X=X, W=W)
    XtWX_inv = np.linalg.inv(XtWX)

    # W^(1/2)*X
    WsqrtX = np.dot(Wsqrt, X)

    # X'*W^(1/2)
    XtWsqrt = np.dot(X.T, Wsqrt)

    return np.dot(WsqrtX, np.dot(XtWX_inv, XtWsqrt))


def cook_dist(model, X, good):
    # Weight matrix
    W = _weight_matrix(model)

    # Hat matrix
    H = _hat_matrix(X, W)
    hii = np.diag(H)  # Diagonal values of hat matrix # fit.get_influence().hat_matrix_diag

    # Pearson residuals
    r = model.resid_pearson

    # Cook's distance (formula used by R = (res/(1 - hat))^2 * hat/(dispersion * p))
    # Note: dispersion is 1 since we aren't modeling overdispersion

    resid = good.disp - model.predict(good)
    rss = np.sum(resid ** 2)
    MSE = rss / (good.shape[0] - 2)
    # use the formula from: https://www.mathworks.com/help/stats/cooks-distance.html
    cooks_d = r**2 / (2 * MSE)  * hii / (1 - hii)**2 #(r / (1 - hii)) ** 2 *  / (1 * 2)

    return cooks_d


def get_layer_keys(adata, layers='all', include_protein=True):
    """Get the list of available layers' keys.
    """
    layer_keys = list(adata.layers.keys())
    if 'protein' in adata.obsm.keys() and include_protein:
        layer_keys.extend(['X', 'protein'])
    else:
        layer_keys.extend(['X'])
    layers = layer_keys if layers is 'all' else list(set(layer_keys).intersection(layers))

    return layers

def get_shared_counts(adata, layers, min_shared_count, type='gene'):
    layers = list(set(layers).difference(['X', 'matrix', 'ambiguous']))

    _nonzeros = reduce(lambda a, b: (adata.layers[a] > 0).multiply(adata.layers[b] > 0), layers) if \
        issparse(adata.layers[layers[0]]) else \
        reduce(lambda a, b: (adata.layers[a] > 0) * (adata.layers[b] > 0), layers)

    _sum = reduce(lambda a, b: _nonzeros.multiply(adata.layers[a]) + _nonzeros.multiply(adata.layers[b]), layers) if \
        issparse(adata.layers[layers[0]]) else \
        reduce(lambda a, b: _nonzeros.multiply(adata.layers[a]) + _nonzeros.multiply(adata.layers[b]), layers)

    if type == 'gene':
        return np.array(_sum.sum(0).A1 > min_shared_count) if issparse(adata.layers[layers[0]]) else np.array(_sum.sum(0) > min_shared_count)
    if type == 'cells':
        return np.array(_sum.sum(1).A1 > min_shared_count) if issparse(adata.layers[layers[0]]) else np.array(_sum.sum(1) > min_shared_count)
