from pathlib import PurePath
import pandas as pd
from common.d_logger import Logs

logger = Logs().get_logger("main")


class EmrTransactionReader():
    def __init__(self, filename, parent):
        self.parent = parent
        self.filename = filename

    def read_df_from(self) -> pd.DataFrame or None:
        code_df = self.parent.sku_model.get_bitcode_df()

        try:
            if PurePath(self.filename).suffix == '.xlsx':
                logger.debug(f"{self.filename} is being imported ... format xlsx")
                bit_df = pd.read_excel(self.filename)
            elif PurePath(self.filename).suffix == '.csv':
                logger.debug(f"{self.filename} is being imported ... format csv")
                bit_df = pd.read_csv(self.filename, sep="\t", encoding='utf-16')
            else:
                logger.error(f"Not implemented importing file type {self.filename}")
                return

            bit_df = bit_df.loc[:, ['처방코드', '총소모량']]
            # strip any white spaces in code names
            bit_df.loc[:, 'bit_code'] = bit_df['처방코드'].str.strip()

            # expand a comma separated bit_codes vertically by using 'explode'
            # which can be applied to a list-like element
            code_df.loc[:, 'bit_code'] = code_df['bit_code'].str.split(',')
            code_df = code_df.explode('bit_code', ignore_index=True)

            # extract only the rows of interest from bit_df using code_df
            merged_df = pd.merge(code_df, bit_df, on='bit_code')

            merged_df = merged_df.astype({"총소모량": "int64"})
            # df with index of 'sku_id' and a column "총소모량"
            merged_df = merged_df.groupby(by=['sku_id'], dropna=True).sum().loc[:, ["총소모량"]]
            merged_df = merged_df.rename(columns={"총소모량": "tr_qty"})

            # append a sku_name column to the df to be returned
            sku_df = self.parent.sku_model.model_df[["sku_id", "sku_name"]]
            ret_df = pd.merge(merged_df, sku_df, left_index=True, right_on="sku_id")
            logger.debug(f"\n{ret_df}")
            return ret_df
        except Exception as e:
            logger.error(e)
            return None


if __name__ == "__main__":
    reader = EmrTransactionReader("bit_doc.xlsx")
    result = reader.read_df_from(['noci40,noci40_fr', 'noci120,noci120_fr'])
    print(result)
