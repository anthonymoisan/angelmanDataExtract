import argparse
import configparser
import sys
from pathlib import Path
from typing import Iterable, Union, Callable, List

import pandas as pd


# ----------------- Agrégateurs -----------------
def first_non_null(s: pd.Series):
    s = s.replace("", pd.NA).dropna()
    return s.iloc[0] if not s.empty else pd.NA

def last_non_null(s: pd.Series):
    s = s.replace("", pd.NA).dropna()
    return s.iloc[-1] if not s.empty else pd.NA


# ----------------- Normalisation clé -----------------
def normalize_key_column(df: pd.DataFrame, key: str, drop_missing_keys: bool, do_normalize: bool) -> pd.DataFrame:
    df = df.copy()
    # Convertit en string, retire espaces
    df[key] = df[key].astype(str)
    if do_normalize:
        df[key] = df[key].str.strip().str.lower()
    else:
        df[key] = df[key].str.strip()

    if drop_missing_keys:
        # Supprime lignes sans clé (NaN, vide, espaces)
        df = df[df[key].notna() & (df[key] != "")]
    return df


# ----------------- Fusion N DataFrames -----------------
def union_no_dupes_many(
    dfs: Iterable[pd.DataFrame],
    key: str,
    agg: Union[str, Callable[[pd.Series], object]] = "first_non_null",
) -> pd.DataFrame:
    """
    Union de N DataFrames (mêmes colonnes) sans doublons sur `key`.
    - Tri systématique par `key` (ordre ascendant, stable).
    - Agrégation uniforme sur toutes les colonnes != key :
      * 'first_non_null' : première valeur non vide/non nulle
      * 'last_non_null'  : dernière valeur non vide/non nulle
    """
    dfs = list(dfs)
    if not dfs:
        return pd.DataFrame()

    base_cols = list(dfs[0].columns)
    if key not in base_cols:
        raise ValueError(f"Clé '{key}' absente des colonnes.")
    for i, d in enumerate(dfs[1:], start=2):
        if list(d.columns) != base_cols:
            raise ValueError(f"df#{i} n'a pas exactement les mêmes colonnes que df#1.")

    both = pd.concat(dfs, ignore_index=True)
    both = both.sort_values(by=[key], ascending=[True], kind="mergesort")

    if callable(agg):
        agg_fn = agg
    elif agg == "first_non_null":
        agg_fn = first_non_null
    elif agg == "last_non_null":
        agg_fn = last_non_null
    else:
        raise ValueError("`strategy` doit être 'first_non_null' ou 'last_non_null'.")

    agg_map = {col: agg_fn for col in both.columns if col != key}
    out = both.groupby(key, as_index=False, sort=False).agg(agg_map)

    cols = [key] + [c for c in out.columns if c != key]
    return out[cols]


# ----------------- Lecture fichiers -----------------
def read_dataframe(path: Path) -> pd.DataFrame:
    ext = path.suffix.lower()
    if ext in [".csv", ".txt"]:
        return pd.read_csv(path,sep=";")
    if ext in [".xlsx", ".xls"]:
        # utilise la première feuille par défaut
        return pd.read_excel(path)
    raise ValueError(f"Format non supporté: {path.name} (extensions supportées: CSV, XLSX)")


# ----------------- Écriture Excel -----------------
def write_excel(df: pd.DataFrame, out_path: Path, sheet_name: str = "Union"):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)


# ----------------- Main -----------------
def run_from_ini(ini_path: Path):
    if not ini_path.exists():
        raise FileNotFoundError(f"INI introuvable: {ini_path}")

    config = configparser.ConfigParser()
    config.read(ini_path, encoding="utf-8")

    if "union" not in config:
        raise ValueError("Section [union] absente dans le fichier INI.")

    section = config["union"]

    key = section.get("key", "").strip()
    if not key:
        raise ValueError("Paramètre 'key' manquant dans [union].")

    strategy = section.get("strategy", "first_non_null").strip()
    drop_missing_keys = section.getboolean("drop_missing_keys", fallback=True)
    normalize_key = section.getboolean("normalize_key", fallback=True)

    inputs = section.get("input_files", "").strip()
    if not inputs:
        raise ValueError("Paramètre 'input_files' manquant dans [union].")
    input_files = [Path(s.strip()) for s in inputs.split(",") if s.strip()]

    out_file = section.get("output_file", "").strip()
    if not out_file:
        raise ValueError("Paramètre 'output_file' manquant dans [union].")
    out_path = Path(out_file)

    sheet_name = section.get("output_sheet", "Union").strip() or "Union"

    # Lecture et pré-traitement des DataFrames
    dataframes: List[pd.DataFrame] = []
    for p in input_files:
        if not p.exists():
            raise FileNotFoundError(f"Fichier d'entrée introuvable: {p}")
        df = read_dataframe(p)
       
        if key not in df.columns:
            raise ValueError(f"Clé '{key}' absente dans {p}")
        df = normalize_key_column(df, key, drop_missing_keys, normalize_key)
        dataframes.append(df)

    # Fusion
    result = union_no_dupes_many(dataframes, key=key, agg=strategy)

    # Export Excel
    write_excel(result, out_path, sheet_name=sheet_name)
    print(f"✅ Consolidation terminée. Fichier généré: {out_path}")


def main():
    parser = argparse.ArgumentParser(description="Union N DataFrames selon un INI")
    parser.add_argument("--config", "-c", required=True, help="Chemin du fichier INI")
    args = parser.parse_args()
    try:
        run_from_ini(Path(args.config))
    except Exception as e:
        print(f"❌ Erreur: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    '''Attention avec le séparateur si fichier CSV ; en français et , en anglais'''
    main()
