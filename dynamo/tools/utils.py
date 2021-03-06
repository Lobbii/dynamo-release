import numpy as np
from scipy.sparse import issparse, csr_matrix
from .moments import strat_mom, MomData, Estimation
import warnings


# ---------------------------------------------------------------------------------------------------
# others
def get_mapper():
    mapper = {'X_spliced': 'M_s', 'X_unspliced': 'M_u', 'X_new': 'M_n', 'X_old': 'M_o', 'X_total': 'M_t',
              'X_uu': 'M_uu', 'X_ul': 'M_ul', 'X_su': 'M_su', 'X_sl': 'M_sl', 'X_protein': 'M_p', 'X': 'M_s'}
    return mapper

def get_finite_inds(X, ax=0):
    finite_inds = np.isfinite(X.sum(ax).A1) if issparse(X) else np.isfinite(X.sum(ax))

    return finite_inds

# ---------------------------------------------------------------------------------------------------
# moment related:
def cal_12_mom(data, t):
    t_uniq = np.unique(t)
    m, v = np.zeros((data.shape[0], len(t_uniq))), np.zeros((data.shape[0], len(t_uniq)))
    for i in range(data.shape[0]):
        data_ = np.array(data[i].A.flatten(), dtype=float) if issparse(data) else np.array(data[i], dtype=float)  # consider using the `adata.obs_vector`, `adata.var_vector` methods or accessing the array directly.
        m[i], v[i] = strat_mom(data_, t, np.nanmean), strat_mom(data_, t, np.nanvar)

    return m, v, t_uniq


# ---------------------------------------------------------------------------------------------------
# dynamics related:
def get_valid_inds(adata, filter_gene_mode):
    if filter_gene_mode == 'final':
        valid_ind = adata.var.use_for_dynamo.values
        # import warnings
        # from scipy.sparse import SparseEfficiencyWarning
        # warnings.simplefilter('ignore', SparseEfficiencyWarning)
    elif filter_gene_mode == 'basic':
        valid_ind = adata.var.pass_basic_filter.values
    elif filter_gene_mode == 'no':
        valid_ind = np.repeat([True], adata.shape[1])

    return valid_ind

def get_data_for_velocity_estimation(subset_adata, mode, use_smoothed, tkey, protein_names, experiment_type, log_unnormalized):
    U, Ul, S, Sl, P = None, None, None, None, None  # U: unlabeled unspliced; S: unlabel spliced: S
    normalized, has_splicing, has_labeling, has_protein = False, False, False, False

    mapper = get_mapper()

    if 'X_unspliced' in subset_adata.layers.keys():
        has_splicing, normalized, assumption_mRNA = True, True, 'ss'
        U = subset_adata.layers[mapper['X_unspliced']].T if use_smoothed else subset_adata.layers['X_unspliced'].T
    elif 'unspliced' in subset_adata.layers.keys():
        has_splicing, assumption_mRNA = True, 'ss'
        raw, row_unspliced = subset_adata.layers['unspliced'].T, subset_adata.layers['unspliced'].T
        if issparse(raw):
            raw.data = np.log(raw.data + 1) if log_unnormalized else raw.data
        else:
            raw = np.log(raw + 1) if log_unnormalized else raw
        U = raw
    if 'X_spliced' in subset_adata.layers.keys():
        S = subset_adata.layers[mapper['X_spliced']].T if use_smoothed else subset_adata.layers['X_spliced'].T
    elif 'spliced' in subset_adata.layers.keys():
        raw, raw_spliced = subset_adata.layers['spliced'].T, subset_adata.layers['spliced'].T
        if issparse(raw):
            raw.data = np.log(raw.data + 1) if log_unnormalized else raw.data
        else:
            raw = np.log(raw + 1) if log_unnormalized else raw
        S = raw

    elif 'X_new' in subset_adata.layers.keys():  # run new / total ratio (NTR)
        has_labeling, normalized, assumption_mRNA = True, True, 'ss'
        U = subset_adata.layers[mapper['X_total']].T - subset_adata.layers[mapper['X_new']].T if use_smoothed else \
        subset_adata.layers['X_total'].T - subset_adata.layers['X_new'].T
        Ul = subset_adata.layers[mapper['X_new']].T if use_smoothed else subset_adata.layers['X_new'].T
    elif 'new' in subset_adata.layers.keys():
        has_labeling, assumption_mRNA = True, 'ss'
        raw, raw_new, old = subset_adata.layers['new'].T, subset_adata.layers['new'].T, subset_adata.layers['total'].T - \
                            subset_adata.layers['new'].T
        if issparse(raw):
            raw.data = np.log(raw.data + 1) if log_unnormalized else raw.data
            old.data = np.log(old.data + 1) if log_unnormalized else old.data
        else:
            raw = np.log(raw + 1) if log_unnormalized else raw
            old = np.log(old + 1) if log_unnormalized else old
        U = old
        Ul = raw

    elif 'X_uu' in subset_adata.layers.keys():  # only uu, ul, su, sl provided
        has_splicing, has_labeling, normalized = True, True, True
        U = subset_adata.layers[mapper['X_uu']].T if use_smoothed else subset_adata.layers[
            'X_uu'].T  # unlabel unspliced: U
    elif 'uu' in subset_adata.layers.keys():
        has_splicing, has_labeling, normalized = True, True, False
        raw, raw_uu = subset_adata.layers['uu'].T, subset_adata.layers['uu'].T
        if issparse(raw):
            raw.data = np.log(raw.data + 1) if log_unnormalized else raw.data
        else:
            raw = np.log(raw + 1) if log_unnormalized else raw
        U = raw
    if 'X_ul' in subset_adata.layers.keys():
        Ul = subset_adata.layers[mapper['X_ul']].T if use_smoothed else subset_adata.layers['X_ul'].T
    elif 'ul' in subset_adata.layers.keys():
        raw, raw_ul = subset_adata.layers['ul'].T, subset_adata.layers['ul'].T
        if issparse(raw):
            raw.data = np.log(raw.data + 1) if log_unnormalized else raw.data
        else:
            raw = np.log(raw + 1) if log_unnormalized else raw
        Ul = raw
    if 'X_sl' in subset_adata.layers.keys():
        Sl = subset_adata.layers[mapper['X_sl']].T if use_smoothed else subset_adata.layers['X_sl'].T
    elif 'sl' in subset_adata.layers.keys():
        raw, raw_sl = subset_adata.layers['sl'].T, subset_adata.layers['sl'].T
        if issparse(raw):
            raw.data = np.log(raw.data + 1) if log_unnormalized else raw.data
        else:
            raw = np.log(raw + 1) if log_unnormalized else raw
        Sl = raw
    if 'X_su' in subset_adata.layers.keys():  # unlabel spliced: S
        S = subset_adata.layers[mapper['X_su']].T if use_smoothed else subset_adata.layers['X_su'].T
    elif 'su' in subset_adata.layers.keys():
        raw, raw_su = subset_adata.layers['su'].T, subset_adata.layers['su'].T
        if issparse(raw):
            raw.data = np.log(raw.data + 1) if log_unnormalized else raw.data
        else:
            raw = np.log(raw + 1) if log_unnormalized else raw
        S = raw

    ind_for_proteins = None
    if 'X_protein' in subset_adata.obsm.keys():
        P = subset_adata.layers[mapper['X_protein']].T if use_smoothed else subset_adata.obsm['X_protein'].T
    elif 'protein' in subset_adata.obsm.keys():
        P = subset_adata.obsm['protein'].T
    if P is not None:
        has_protein = True
        if protein_names is None:
            warnings.warn(
                'protein layer exists but protein_names is not provided. No estimation will be performed for protein data.')
        else:
            protein_names = list(set(subset_adata.var.index).intersection(protein_names))
            ind_for_proteins = [np.where(subset_adata.var.index == i)[0][0] for i in protein_names]
            subset_adata.var['is_protein_velocity_genes'] = False
            subset_adata.var.loc[ind_for_proteins, 'is_protein_velocity_genes'] = True

    if experiment_type is not None or mode is 'moment':
        assumption_mRNA = None

    if has_labeling:
        if tkey in subset_adata.obs.columns:
            t = np.array(subset_adata.obs[tkey], dtype='float')
        else:
            raise Exception('the tkey ', tkey, ' provided is not a valid column name in .obs.')
    else:
        t = None

    return U, Ul, S, Sl, P, t, normalized, has_splicing, has_labeling, has_protein, ind_for_proteins, assumption_mRNA

def set_velocity(adata, vel_U, vel_S, vel_P, _group, cur_grp, cur_cells_bools, valid_ind, ind_for_proteins):
    if type(vel_U) is not float:
        if cur_grp == _group[0]: adata.layers['velocity_U'] = csr_matrix((adata.shape))
        tmp = csr_matrix((np.sum(cur_cells_bools), adata.shape[1]))
        tmp[:, valid_ind] = vel_U.T.tocsr() if issparse(vel_U) else csr_matrix(vel_U.T)
        adata.layers['velocity_U'][cur_cells_bools, :] = tmp  # np.where(valid_ind)[0] required for sparse matrix
    if type(vel_S) is not float:
        if cur_grp == _group[0]: adata.layers['velocity_S'] = csr_matrix((adata.shape))
        tmp = csr_matrix((np.sum(cur_cells_bools), adata.shape[1]))
        tmp[:, valid_ind] = vel_S.T.tocsr() if issparse(vel_S) else csr_matrix(vel_S.T)
        adata.layers['velocity_S'][cur_cells_bools, :] = tmp  # np.where(valid_ind)[0] required for sparse matrix
    if type(vel_P) is not float:
        if cur_grp == _group[0]: adata.obsm['velocity_P'] = csr_matrix((adata.obsm['P'].shape[0], len(ind_for_proteins)))
        adata.obsm['velocity_P'][cur_cells_bools, :] = vel_P.T.tocsr() if issparse(vel_P) else csr_matrix(vel_P.T)

    return adata

def set_param_deterministic(adata, est, alpha, beta, gamma, eta, delta, experiment_type,_group, cur_grp, kin_param_pre, valid_ind, ind_for_proteins):
    if experiment_type is 'mix_std_stm':
        if alpha is not None:
            if cur_grp == _group[0]: adata.varm[kin_param_pre + 'alpha'] = np.zeros((adata.shape[1], alpha[1].shape[1]))
            adata.varm[kin_param_pre + 'alpha'][valid_ind, :] = alpha[1]
            adata.var[kin_param_pre + 'alpha'], adata.var[kin_param_pre + 'alpha_std'] = None, None
            adata.var.loc[valid_ind, kin_param_pre + 'alpha'], adata.var.loc[
                valid_ind, kin_param_pre + 'alpha_std'] = alpha[1][:, -1], alpha[0]

        if cur_grp == _group[0]: adata.var[kin_param_pre + 'beta'], adata.var[kin_param_pre + 'gamma'], adata.var[
            kin_param_pre + 'half_life'] = None, None, None

        adata.var.loc[valid_ind, kin_param_pre + 'beta'] = beta
        adata.var.loc[valid_ind, kin_param_pre + 'gamma'] = gamma
        adata.var.loc[valid_ind, kin_param_pre + 'half_life'] = np.log(2) / gamma
    else:
        if alpha is not None:
            if len(alpha.shape) > 1:  # for each cell
                if cur_grp == _group[0]: adata.varm[kin_param_pre + 'alpha'] = np.zeros((alpha.shape))  # adata.shape
                adata.varm[kin_param_pre + 'alpha'] = alpha  # [:, valid_ind]
                adata.var.loc[valid_ind, kin_param_pre + 'alpha'] = alpha.mean(1)
            elif len(alpha.shape) is 1:
                if cur_grp == _group[0]: adata.var[kin_param_pre + 'alpha'] = None
                adata.var.loc[valid_ind, kin_param_pre + 'alpha'] = alpha

        if cur_grp == _group[0]: adata.var[kin_param_pre + 'beta'], adata.var[kin_param_pre + 'gamma'], adata.var[
            kin_param_pre + 'half_life'] = None, None, None
        adata.var.loc[valid_ind, kin_param_pre + 'beta'] = beta
        adata.var.loc[valid_ind, kin_param_pre + 'gamma'] = gamma
        adata.var.loc[valid_ind, kin_param_pre + 'half_life'] = np.log(2) / gamma

        alpha_intercept, alpha_r2, gamma_intercept, gamma_r2, delta_intercept, delta_r2, uu0, ul0, su0, sl0, U0, S0, total0 = \
            est.aux_param.values()
        if alpha_r2 is not None:
            alpha_r2[~np.isfinite(alpha_r2)] = 0
        if cur_grp == _group[0]: adata.var[kin_param_pre + 'alpha_b'], adata.var[kin_param_pre + 'alpha_r2'], \
                                 adata.var[kin_param_pre + 'gamma_b'], adata.var[kin_param_pre + 'gamma_r2'], \
                                 adata.var[kin_param_pre + 'delta_b'], adata.var[kin_param_pre + 'delta_r2'], \
                                 adata.var[kin_param_pre + 'uu0'], adata.var[kin_param_pre + 'ul0'], \
                                 adata.var[kin_param_pre + 'su0'], adata.var[kin_param_pre + 'sl0'], \
                                 adata.var[kin_param_pre + 'U0'], adata.var[kin_param_pre + 'S0'], \
                                 adata.var[
                                     kin_param_pre + 'total0'] = None, None, None, None, None, None, None, None, None, None, None, None, None

        adata.var.loc[valid_ind, kin_param_pre + 'alpha_b'] = alpha_intercept
        adata.var.loc[valid_ind, kin_param_pre + 'alpha_r2'] = alpha_r2

        if gamma_r2 is not None:
            gamma_r2[~np.isfinite(gamma_r2)] = 0
        adata.var.loc[valid_ind, kin_param_pre + 'gamma_b'] = gamma_intercept
        adata.var.loc[valid_ind, kin_param_pre + 'gamma_r2'] = gamma_r2

        adata.var.loc[valid_ind, kin_param_pre + 'uu0'] = uu0
        adata.var.loc[valid_ind, kin_param_pre + 'ul0'] = ul0
        adata.var.loc[valid_ind, kin_param_pre + 'su0'] = su0
        adata.var.loc[valid_ind, kin_param_pre + 'sl0'] = sl0
        adata.var.loc[valid_ind, kin_param_pre + 'U0'] = U0
        adata.var.loc[valid_ind, kin_param_pre + 'S0'] = S0
        adata.var.loc[valid_ind, kin_param_pre + 'total0'] = total0

        if ind_for_proteins is not None:
            delta_r2[~np.isfinite(delta_r2)] = 0
            if cur_grp == _group[0]: adata.var[kin_param_pre + 'eta'], adata.var[kin_param_pre + 'delta'], \
                                     adata.var[kin_param_pre + 'delta_b'], adata.var[kin_param_pre + 'delta_r2'], \
                                     adata.var[kin_param_pre + 'p_half_life'] = None, None, None, None, None
            adata.var.loc[valid_ind, kin_param_pre + 'eta'][ind_for_proteins] = eta
            adata.var.loc[valid_ind, kin_param_pre + 'delta'][ind_for_proteins] = delta
            adata.var.loc[valid_ind, kin_param_pre + 'delta_b'][ind_for_proteins] = delta_intercept
            adata.var.loc[valid_ind, kin_param_pre + 'delta_r2'][ind_for_proteins] = delta_r2
            adata.var.loc[valid_ind, kin_param_pre + 'p_half_life'][ind_for_proteins] = np.log(2) / delta

    return adata

def set_param_moment(adata, a, b, alpha_a, alpha_i, beta, gamma, kin_param_pre, _group, cur_grp, valid_ind):
    if cur_grp == _group[0]: adata.var[kin_param_pre + 'a'], adata.var[kin_param_pre + 'b'], adata.var[
        kin_param_pre + 'alpha_a'], \
                             adata.var[kin_param_pre + 'alpha_i'], adata.var[kin_param_pre + 'beta'], adata.var[
                                 kin_param_pre + 'p_half_life'], \
                             adata.var[kin_param_pre + 'gamma'], adata.var[
                                 kin_param_pre + 'half_life'] = None, None, None, None, None, None, None, None

    adata.var.loc[valid_ind, kin_param_pre + 'a'] = a
    adata.var.loc[valid_ind, kin_param_pre + 'b'] = b
    adata.var.loc[valid_ind, kin_param_pre + 'alpha_a'] = alpha_a
    adata.var.loc[valid_ind, kin_param_pre + 'alpha_i'] = alpha_i
    adata.var.loc[valid_ind, kin_param_pre + 'beta'] = beta
    adata.var.loc[valid_ind, kin_param_pre + 'gamma'] = gamma
    adata.var.loc[valid_ind, kin_param_pre + 'half_life'] = np.log(2) / gamma

    return adata

def get_U_S_for_velocity_estimation(subset_adata, use_smoothed, has_splicing, has_labeling, log_unnormalized, NTR):
    mapper = get_mapper()

    if has_splicing:
        if has_labeling:
            if 'X_uu' in subset_adata.layers.keys():  # unlabel spliced: S
                if use_smoothed:
                    uu, ul, su, sl = subset_adata.layers[mapper['X_uu']].T, subset_adata.layers[mapper['X_ul']].T, \
                                     subset_adata.layers[mapper['X_su']].T, subset_adata.layers[mapper['X_sl']].T
                else:
                    uu, ul, su, sl = subset_adata.layers['X_uu'].T, subset_adata.layers['X_ul'].T, \
                                     subset_adata.layers['X_su'].T, subset_adata.layers['X_sl'].T
            else:
                uu, ul, su, sl = subset_adata.layers['uu'].T, subset_adata.layers['ul'].T, \
                                 subset_adata.layers['su'].T, subset_adata.layers['sl'].T
                if issparse(uu):
                    uu.data = np.log(uu.data + 1) if log_unnormalized else uu.data
                    ul.data = np.log(ul.data + 1) if log_unnormalized else ul.data
                    su.data = np.log(su.data + 1) if log_unnormalized else su.data
                    sl.data = np.log(sl.data + 1) if log_unnormalized else sl.data
                else:
                    uu = np.log(uu + 1) if log_unnormalized else uu
                    ul = np.log(ul + 1) if log_unnormalized else ul
                    su = np.log(su + 1) if log_unnormalized else su
                    sl = np.log(sl + 1) if log_unnormalized else sl
            ul, sl = (ul + sl, uu + ul + su + sl) if NTR else (ul, sl)
        else:
            if ('X_unspliced' in subset_adata.layers.keys()) or (mapper['X_unspliced'] in subset_adata.layers.keys()):  # unlabel spliced: S
                if use_smoothed:
                    ul, sl = subset_adata.layers[mapper['X_unspliced']].T, subset_adata.layers[mapper['X_spliced']].T
                else:
                    ul, sl = subset_adata.layers['X_unspliced'].T, subset_adata.layers['X_spliced'].T
            else:
                ul, sl = subset_adata.layers['unspliced'].T, subset_adata.layers['spliced'].T
                if issparse(ul):
                    ul.data = np.log(ul.data + 1) if log_unnormalized else ul.data
                    sl.data = np.log(sl.data + 1) if log_unnormalized else sl.data
                else:
                    ul = np.log(ul + 1) if log_unnormalized else ul
                    sl = np.log(sl + 1) if log_unnormalized else sl
        U, S = ul, sl
    else:
        if ('X_new' in subset_adata.layers.keys()) or (mapper['X_new'] in subset_adata.layers.keys):  # run new / total ratio (NTR)
            if use_smoothed:
                U = subset_adata.layers[mapper['X_new']].T
                S = subset_adata.layers[mapper['X_total']].T if NTR else subset_adata.layers[mapper['X_total']].T - subset_adata.layers[mapper['X_new']].T
            else:
                U = subset_adata.layers['X_new'].T
                S = subset_adata.layers['X_total'].T if NTR else subset_adata.layers['X_total'].T - subset_adata.layers['X_new'].T
        elif 'new' in subset_adata.layers.keys():
            U = subset_adata.layers['new'].T
            S = subset_adata.layers['total'].T if NTR else subset_adata.layers['total'].T - subset_adata.layers['new'].T
            if issparse(U):
                U.data = np.log(U.data + 1) if log_unnormalized else U.data
                S.data = np.log(S.data + 1) if log_unnormalized else S.data
            else:
                U = np.log(U + 1) if log_unnormalized else U
                S = np.log(S + 1) if log_unnormalized else S

    return U, S

def moment_model(adata, subset_adata, _group, cur_grp, log_unnormalized, tkey):
    # a few hard code to set up data for moment mode:
    if 'uu' in subset_adata.layers.keys() or 'X_uu' in subset_adata.layers.keys():
        if log_unnormalized and 'X_uu' not in subset_adata.layers.keys():
            if issparse(subset_adata.layers['uu']):
                subset_adata.layers['uu'].data, subset_adata.layers['ul'].data, subset_adata.layers['su'].data, \
                subset_adata.layers['sl'].data = \
                    np.log(subset_adata.layers['uu'].data + 1), np.log(subset_adata.layers['ul'].data + 1), np.log(
                        subset_adata.layers['su'].data + 1), np.log(subset_adata.layers['sl'].data + 1)
            else:
                subset_adata.layers['uu'], subset_adata.layers['ul'], subset_adata.layers['su'], subset_adata.layers[
                    'sl'] = \
                    np.log(subset_adata.layers['uu'] + 1), np.log(subset_adata.layers['ul'] + 1), np.log(
                        subset_adata.layers['su'] + 1), np.log(subset_adata.layers['sl'] + 1)

        subset_adata_u, subset_adata_s = subset_adata.copy(), subset_adata.copy()
        del subset_adata_u.layers['su'], subset_adata_u.layers['sl'], subset_adata_s.layers['uu'], \
        subset_adata_s.layers['ul']
        subset_adata_u.layers['new'], subset_adata_u.layers['old'], subset_adata_s.layers['new'], subset_adata_s.layers[
            'old'] = \
            subset_adata_u.layers.pop('ul'), subset_adata_u.layers.pop('uu'), subset_adata_s.layers.pop(
                'sl'), subset_adata_s.layers.pop('su')
        Moment, Moment_ = MomData(subset_adata_s, tkey), MomData(subset_adata_u, tkey)
        if cur_grp == _group[0]:
            t_ind = 0
            g_len, t_len = len(_group), len(np.unique(adata.obs[tkey]))
            adata.uns['M_sl'], adata.uns['V_sl'], adata.uns['M_ul'], adata.uns['V_ul'] = \
                np.zeros((adata.shape[1], g_len * t_len)), np.zeros((adata.shape[1], g_len * t_len)), np.zeros(
                    (adata.shape[1], g_len * t_len)), np.zeros((adata.shape[1], g_len * t_len))

        adata.uns['M_sl'][:, (t_len * t_ind):(t_len * (t_ind + 1))], \
        adata.uns['V_sl'][:, (t_len * t_ind):(t_len * (t_ind + 1))], \
        adata.uns['M_ul'][:, (t_len * t_ind):(t_len * (t_ind + 1))], \
        adata.uns['V_ul'][:, (t_len * t_ind):(t_len * (t_ind + 1))] = Moment.M, Moment.V, Moment_.M, Moment_.V

        del Moment_
        Est = Estimation(Moment, adata_u=subset_adata_u, time_key=tkey, normalize=True)  # # data is already normalized
    else:
        if log_unnormalized and 'X_total' not in subset_adata.layers.keys():
            if issparse(subset_adata.layers['total']):
                subset_adata.layers['new'].data, subset_adata.layers['total'].data = np.log(
                    subset_adata.layers['new'].data + 1), np.log(subset_adata.layers['total'].data + 1)
            else:
                subset_adata.layers['total'], subset_adata.layers['total'] = np.log(
                    subset_adata.layers['new'] + 1), np.log(subset_adata.layers['total'] + 1)

        Moment = MomData(subset_adata, tkey)
        if cur_grp == _group[0]:
            t_ind = 0
            g_len, t_len = len(_group), len(np.unique(adata.obs[tkey]))
            adata.uns['M'], adata.uns['V'] = np.zeros((adata.shape[1], g_len * t_len)), np.zeros(
                (adata.shape[1], g_len * t_len))

        adata.uns['M'][:, (t_len * t_ind):(t_len * (t_ind + 1))], adata.uns['V'][:, (t_len * t_ind):(
                    t_len * (t_ind + 1))] = Moment.M, Moment.V
        Est = Estimation(Moment, time_key=tkey, normalize=True)  # # data is already normalized

    return adata, Est, t_ind

# ---------------------------------------------------------------------------------------------------
# estimation related
def lhsclassic(n_samples, n_dim):

    # From PyDOE
    # Generate the intervals
    cut = np.linspace(0, 1, n_samples + 1)

    # Fill points uniformly in each interval
    u = np.random.rand(n_samples, n_dim)
    a = cut[:n_samples]
    b = cut[1:n_samples + 1]
    rdpoints = np.zeros(u.shape)
    for j in range(n_dim):
        rdpoints[:, j] = u[:, j] * (b - a) + a

    # Make the random pairings
    H = np.zeros(rdpoints.shape)
    for j in range(n_dim):
        order = np.random.permutation(range(n_samples))
        H[:, j] = rdpoints[order, j]

    return H


def norm_loglikelihood(x, mu, sig):
    """Calculate log-likelihood for the data.
    """
    ll = - 0.5 * np.log(2 * np.pi) - 0.5 * (x - mu)**2 / sig**2

    return np.sum(ll)

# ---------------------------------------------------------------------------------------------------
# velocity related
def set_velocity_genes(adata, vkey='velocity_S', min_r2=0.1, use_for_dynamo=True):
    layer = vkey.split('_')[1]

    if layer is 'U':
        adata.var['use_for_velocity'] = (adata.var.alpha_r2 > min_r2) & adata.var.use_for_dynamo if use_for_dynamo \
            else adata.var.alpha_r2 > min_r2
    elif layer is 'S':
        adata.var['use_for_velocity'] = (adata.var.gamma_r2 > min_r2) & adata.var.use_for_dynamo if use_for_dynamo \
            else adata.var.gamma_r2 > min_r2
    elif layer is 'P':
        adata.var['use_for_velocity'] = (adata.var.delta_r2 > min_r2) & adata.var.use_for_dynamo if use_for_dynamo \
            else adata.var.delta_r2 > min_r2

    return adata

def get_ekey_vkey_from_adata(adata):

    dynamics_key = [i for i in adata.uns.keys() if i.endswith('dynamics')][0]
    experiment_type, use_smoothed = adata.uns[dynamics_key]['experiment_type'], adata.uns[dynamics_key]['use_smoothed']
    has_splicing, has_labeling = adata.uns[dynamics_key]['has_splicing'], adata.uns[dynamics_key]['has_labeling']
    NTR = adata.uns[dynamics_key]['NTR_vel']

    mapper = get_mapper()

    if has_splicing:
        if has_labeling:
            if 'X_uu' in adata.layers.keys():  # unlabel spliced: S
                if use_smoothed:
                    uu, ul, su, sl = adata.layers[mapper['X_uu']], adata.layers[mapper['X_ul']], adata.layers[mapper['X_su']], adata.layers[mapper['X_sl']]
                    ul, sl = (ul + sl, uu + ul + su + sl) if NTR else (ul, sl)
                    adata.layers['M_U'], adata.layers['M_S'] = ul, sl
                else:
                    uu, ul, su, sl = adata.layers['X_uu'], adata.layers['X_ul'], adata.layers['X_su'], adata.layers['X_sl']
                    ul, sl = (ul + sl, uu + ul + su + sl) if NTR else (ul, sl)
                    adata.layers['X_U'], adata.layers['X_S'] = ul, sl
            else:
                raise Exception('The input data you have is not normalized/log trnasformed or smoothed and normalized/log trnasformed!')

            if experiment_type == 'kinetics':
                ekey, vkey = ('M_U', 'velocity_U') if use_smoothed else ('X_U', 'velocity_U')
            elif experiment_type == 'degradation':
                ekey, vkey = ('M_S', 'velocity_S') if use_smoothed else ('X_S', 'velocity_S')
            elif experiment_type == 'one_shot':
                ekey, vkey = ('M_U', 'velocity_U') if use_smoothed else ('X_U', 'velocity_U')
            elif experiment_type == 'mix_std_stm':
                ekey, vkey = ('M_U', 'velocity_U') if use_smoothed else ('X_U', 'velocity_U')
        else:
            if ('X_unspliced' in adata.layers.keys()) or (mapper['X_unspliced'] in adata.layers.keys()):  # unlabel spliced: S
                if use_smoothed:
                    ul, sl = mapper['X_unspliced'], mapper['X_spliced']
                else:
                    ul, sl = 'X_unspliced', 'X_spliced'
            else:
                raise Exception('The input data you have is not normalized/log trnasformed or smoothed and normalized/log trnasformed!')
            ekey, vkey = ('M_s', 'velocity_S') if use_smoothed else ('X_spliced', 'velocity_S')
    else:
        if ('X_new' in adata.layers.keys()) or (mapper['X_new'] in adata.layers.keys):  # run new / total ratio (NTR)
            # we may also create M_U, M_S layers? 
            if experiment_type == 'kinetics':
                ekey, vkey = (mapper['X_new'], 'velocity_U') if use_smoothed else ('X_new', 'velocity_U')
            elif experiment_type == 'degradation':
                ekey, vkey = (mapper['X_total'], 'velocity_S') if use_smoothed else ('X_total', 'velocity_S')
            elif experiment_type == 'one_shot':
                ekey, vkey = (mapper['X_new'], 'velocity_U') if use_smoothed else ('X_new', 'velocity_U')
            elif experiment_type == 'mix_std_stm':
                ekey, vkey = (mapper['X_new'], 'velocity_U') if use_smoothed else ('X_new', 'velocity_U')

        elif 'new' in adata.layers.keys():
            raise Exception(
                'The input data you have is not normalized/log trnasformed or smoothed and normalized/log trnasformed!')

    return ekey, vkey
