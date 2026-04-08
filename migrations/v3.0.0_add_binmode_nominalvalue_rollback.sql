-- Rollback: v3.0.0 — Remove BinMode and NominalValue from ValueBin
-- Reverses: v3.0.0_add_binmode_nominalvalue.sql
-- NOTE: Any 'nominal' or 'interval_with_nominal' axes/bins will be lost; run only on dev/test.

-- ============================================================
-- 1. Revert ValueBin: restore NOT NULL bounds, drop NominalValue
-- ============================================================
ALTER TABLE [dbo].[ValueBin]
    DROP CONSTRAINT [CK_ValueBin_BinValues];
GO

-- Ensure no nulls remain before making NOT NULL (interval-only data assumption)
UPDATE [dbo].[ValueBin]
    SET [LowerBound] = 0, [UpperBound] = 1
    WHERE [LowerBound] IS NULL OR [UpperBound] IS NULL;
GO

ALTER TABLE [dbo].[ValueBin]
    ALTER COLUMN [LowerBound] FLOAT NOT NULL;
GO

ALTER TABLE [dbo].[ValueBin]
    ALTER COLUMN [UpperBound] FLOAT NOT NULL;
GO

ALTER TABLE [dbo].[ValueBin]
    DROP COLUMN [NominalValue];
GO

ALTER TABLE [dbo].[ValueBin]
    ADD CONSTRAINT [CK_ValueBin_Bounds] CHECK (UpperBound > LowerBound);
GO

-- ============================================================
-- 2. Remove BinMode_ID from ValueBinningAxis
-- ============================================================
ALTER TABLE [dbo].[ValueBinningAxis]
    DROP CONSTRAINT [FK_ValueBinningAxis_BinMode];
GO

ALTER TABLE [dbo].[ValueBinningAxis]
    DROP CONSTRAINT [DF_ValueBinningAxis_BinMode];
GO

ALTER TABLE [dbo].[ValueBinningAxis]
    DROP COLUMN [BinMode_ID];
GO

-- ============================================================
-- 3. Drop BinMode table
-- ============================================================
DROP TABLE [dbo].[BinMode];
GO
