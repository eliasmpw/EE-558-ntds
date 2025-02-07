import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import networkx as nx
import json
import timeit
from sklearn.metrics import mean_absolute_error
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, mean_absolute_error
from sklearn.model_selection import train_test_split

def col_json_to_dict(df, cols):
    """Transform the json values inside a column into list of dictionaries
        Args:
            df(pd.Dataframe): dataframe 
            cols(list): name of columns with json values
        Returns:
            A pandas Dataframe with the json columns transformed
    """
    transformed_df = df
    for col in cols:
        transformed_df = transformed_df.assign(**{col: df[col].apply(json.loads)})
    return transformed_df

def col_dict_to_set(df, col, key):
    """Create a set from the values of the dictionaries given a key
        Args:
            df(pd.Dataframe): dataframe
            col(str): column containing list of dictionaries
            key(str): key to extract from the dictionaries
        Returns:
            A pandas Dataframe with the list of dictionaries
            transformed into sets 
    """
    get_set = lambda dict_list: set([dict_.get(key) for dict_ in dict_list])
    return df.assign(**{col: df[col].apply(get_set)})

def col_filter_dict_with_vals(df, col, field, values):
    """Filter dictionaries with specific values from a column with lists of dictionaries
         Args:
             df(pd.Dataframe): dataframe
             col(str): column name
             field(str): field of the dictionary to extract
             values(list): list of values to filter
         Returns:
             A pandas Dataframe with entries filtered 
         
    """
    filter_dicts = lambda dict_list: [
        dict_ for dict_ in dict_list if dict_.get(field) in values
    ]
    return df.assign(**{col: df[col].apply(filter_dicts)})

def get_intersections_length_adj_mat(col):
    """Get the intersection length of the set of each entry with the set of every other entry in the column
        Args:
            col(column): column name 
        Returns:
            A ndarray containing the length of the intersections sets
    """
    start = timeit.default_timer()
    adj = np.zeros((col.shape[0], col.shape[0]))
    for (i, set_row) in col.iteritems():
        for (j, set_col) in col.iteritems():
            try:
                adj[i, j] = len(set_row.intersection(set_col))
            except AttributeError:
                adj[i, j] = 0
    adj_diag = np.diag(np.diag(adj))
    adj = adj - adj_diag
    stop = timeit.default_timer()
    print("Time: ", stop - start)
    return adj

def get_unions_length_adj_mat(col):
    """Get the unions length of the set of each entry with the set of every other entry in the column
        Args:
            col(str): the name of the column
        Returns:
            A ndarray containing the lengths of the union sets
    """
    start = timeit.default_timer()
    adj = np.zeros((col.shape[0], col.shape[0]))
    for (i, set_row) in enumerate(col):
        for (j, set_col) in enumerate(col):
            try:
                adj[i, j] = len(set_row.union(set_col))
            except AttributeError:
                adj[i, j] = 0
    stop = timeit.default_timer()
    print("Time: ", stop - start)
    return adj

def get_json_keys_from_col(col):
    """Get keys from all json strings within a column
        Args:
            col(str): column name
        Returns:
            A list of keys from the dictionaries
            A list of indexes for which the element is not a dictionary
    """
    fields = set()
    col = col.apply(json.loads)
    col = col.dropna()
    not_dict_idx = []
    if len(col[0]) > 1:
        col = col.explode()
    for (i, row) in enumerate(col):
        try:
            fields = fields.union(set(row.keys()))
        except AttributeError:
            not_dict_idx.append(i)
    return list(fields), not_dict_idx

def get_json_values_from_col(col, field):
    """Get values from all json strings within a column
        Args: 
            col(str): column name
            field(str): field from dictionary
        Returns:
            A list of json field values from column
            Index that does not contain a value
    """
    field_values = set()
    col = col.apply(json.loads)
    col = col.dropna()
    not_val_idx = []
    if len(col[0]) > 1:
        col = col.explode()
    for (i, row) in enumerate(col):
        try:
            field_values.add(row[field])
        except (AttributeError, TypeError):
            not_val_idx.append(i)
    return list(field_values), not_val_idx

def sparsify_mat(mat,epsilon):
    """Set the values below a threshold to 0
        Args:
            mat(numpy.ndarray): matrix to sparsify
            epsilon(float): threshold for sparsification
        Returns:
            A sparsified matrix
    """
    return np.where(mat<=epsilon,0,mat)

def log10_transform(epsilon):
    """Return a lambda function to perform a log transform
        Args:
            epsilon(float): value to add to avoid log10(0)
        Returns:
            An anonymous function to calculate the log10
    """
    return lambda x: np.log10(x+epsilon)

def plot_hist(col,title,xlabel,ylabel,log = False, figsize = (10,5), xticks_step = 1.0 , bins = 200, epsilon = 1e-6):
    """Plot a histogram of the column values
        Args:
            col(str): column name
            title(str): title of the plot
            xlabel(str): label of x axis
            ylabel(str): label of y axis
            log(bool): apply a logscale on x axis
            figsize(tuple): figure size
            xticks_step: step between xticks
            bins: number of bins for the histogram
            epsilon: value to add to avoid log10(0)
        Returns:
            A figure 
    """
    if log:
        col = col.apply(log10_transform(epsilon)) 
    fig, ax = plt.subplots()
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_xticks(np.arange(min(col), max(col)+xticks_step,xticks_step))
    col.hist(ax = ax, figsize = figsize, bins = bins, color="teal")
    plt.close()
    return fig

def normalize_vote_rating(
    vote_rating_col,
    vote_count_col,
    names=["vote_average", "vote_count"],
):
    """Normalize vote rating using vote count according to IMDbs formula
        Args: 
            vote_rating_col(str): column containing the vote rating
            vote_count_col(str): column containing the vote count
            names(str): list of column names names to assign in the dataframe
        Returns:
            A dataframe with the normalized vote rating
    """
    c = vote_rating_col.mean()
    m = vote_count_col.min()
    vote_df = pd.concat([vote_rating_col, vote_count_col], axis=1, names=names)
    normalize_vote_rating = (
        lambda row: (row[names[1]] / (row[names[1]] + m)) * row[names[0]] + (m / (row[names[1]] + m)) * c
    )
    return vote_df.apply(normalize_vote_rating,axis=1)

def fit_polynomial(lam: np.ndarray, order: int, spectral_response: np.ndarray):
    """Return an array of polynomial coefficients of length 'order'.
        Args:
            lam(np.ndarray): lambda
            order(int): order of the polynomial
            spectral_response(np.ndarray): spectral_response
        Returns:
            coeff(np.ndarray):
    """
    A = np.vander(lam, order, increasing=True)
    coeff = np.linalg.lstsq(A, spectral_response, rcond=None)[0]
    return coeff

def polynomial_graph_filter_response(coeff: np.array, lam: np.ndarray):
    """ Return an array of the same shape as lam.
        response[i] is the spectral response at frequency lam[i]. """
    response = np.zeros_like(lam)
    for n, c in enumerate(coeff):
        response += c * (lam**n)
    return response

def polynomial_graph_filter(coeff: np.array, laplacian: np.ndarray):
    """ Return the laplacian polynomial with coefficients 'coeff'. """
    power = np.eye(laplacian.shape[0])
    filt = coeff[0] * power
    for n, c in enumerate(coeff[1:]):
        power = laplacian @ power
        filt += c * power
    return filt

def remove_elements_from_list(l,elements):
    elements_set = set(elements)
    mod_l = set(l)
    mod_l = list(mod_l - elements_set)
    return mod_l

def get_linear_reg_results(X,y,test_size,seed):
    X_train, X_test, y_train, y_test = train_test_split(X,y,test_size=test_size,random_state=seed)
    lr = LinearRegression()
    fit_lr =lr.fit(X_train,y_train)
    y_pred = fit_lr.predict(X_test)
    signal_nmae = nmae(y_test,y_pred,"range")
    return y_pred, signal_nmae, fit_lr

def get_train_feats_and_gt(df,gt_col,remove_cols = None):
    """Get the train features and groundtruth col
        
        Args:
            df(pandas.DataFrame):
            gt_col(str)         :
            remove_cols(list)   :
        Returns:
            A numpy.ndarray containing the features
            A numpy.ndarray containing the labels
    """
    df_cols = list(df.columns)
    if remove_cols:
        feat_cols = remove_elements_from_list(df_cols,remove_cols + [gt_col])
    else:
        feat_cols = remove_elements_from_list(df_cols,[gt_col])
    X = df[feat_cols].values
    y = df[gt_col].values
    return X, y

def get_datasets(df,columns):
    cols_2_remove = ["community"]
    Xs = {}
    Xs_com = {}
    ys = {}
    ys_com = {}
    for col in columns:
        X, y = get_train_feats_and_gt(df,col,cols_2_remove)
        X_com, y_com = get_train_feats_and_gt(df,col)
        Xs[col]=X
        Xs_com[col] = X_com
        ys[col] = y
        ys_com[col] = y_com
    return Xs, Xs_com, ys, ys_com

def nmae(y_gt,y_pred,den_type="iqr"):
    """Calculate the normalized mean-absolute error
        
        Can be normalized by 3 quantities calculated on the groundtruth:
        - iqr: 'Interquartile range'
        - range: 'Max-min range'
        - std: 'Standard deviation'
        
        Args:
            y_gt(numpy.ndarray)    :  the groundtruth values
            y_pred(numpy.ndarray)  :  the predicted values
            den_type(str)          :  the type of denominator           
        Returns:
            A float that is the value of the nmae
    """
    if den_type == "iqr":
        den = iqr(y_gt)
    elif den_type == "range":
        den = np.max(y_gt) - np.min(y_gt)
    elif den_type == "std":
        den = np.std(y_gt)
    else:
        raise ValueError("Normalized MAE can only handle iqr, range and std")
    return mean_absolute_error(y_gt,y_pred)/den

def one_hot_encode_feats(X,cols):
    """One hot encode feature
        Args:
            X(numpy.ndarray)                           :   the features
            cols(list)                                 :   list of column numbers of the features to be one-hot encoded
        Returns:
            A numpy.ndarray containing the encoded features
            A OneHotEncoder object       
    """
    enc = OneHotEncoder(handle_unknown="ignore",categorical_features=cols)
    encoded_feats = enc.fit_transform(X)
    return encoded_feats,enc

def attrs_to_graph(g, df):
    """ Adds attributes from dataframe `df` to graph `g` """
    for column in df.columns:
        nx.set_node_attributes(g, df[column].to_dict(), column)
        
def gefx_compatible(x):
    """ Transforms `x` into a gefx compatible variable """
    if isinstance(x, list):
        return ", ".join(list(map(lambda y: str(y), x)))
    return ", ".join(list(map(lambda y: str(y), list(x))))