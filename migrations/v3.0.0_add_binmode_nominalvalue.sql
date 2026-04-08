-- Migration: v3.0.0 — Add BinMode vocabulary table and NominalValue to ValueBin
-- Adds BinMode lookup table, BinMode_ID FK to ValueBinningAxis,
-- makes ValueBin bounds nullable, adds NominalValue, replaces bounds check constraint.
-- Existing bins (all interval) default to BinMode_ID = 1 ('interval').

-- ============================================================
-- 1. Create BinMode vocabulary table and seed it
-- ============================================================
CREATE TABLE [dbo].[BinMode] (
    [BinMode_ID]    INT           NOT NULL,
    [Name]          NVARCHAR(30)  NOT NULL,
    [Description]   NVARCHAR(200),
    CONSTRAINT [PK_BinMode] PRIMARY KEY ([BinMode_ID]),
    CONSTRAINT [UQ_BinMode_Name] UNIQUE ([Name])
);
GO

INSERT INTO [dbo].[BinMode] ([BinMode_ID], [Name], [Description]) VALUES
    (1, N'interval',              N'Bins defined by lower and upper bounds only'),
    (2, N'interval_with_nominal', N'Bins defined by bounds plus a nominal center value'),
    (3, N'nominal',               N'Bins defined by a single nominal value only');
GO

-- ============================================================
-- 2. Add BinMode_ID to ValueBinningAxis (default to 1 = interval)
-- ============================================================
ALTER TABLE [dbo].[ValueBinningAxis]
    ADD [BinMode_ID] INT NOT NULL
    CONSTRAINT [DF_ValueBinningAxis_BinMode] DEFAULT 1;
GO

ALTER TABLE [dbo].[ValueBinningAxis]
    ADD CONSTRAINT [FK_ValueBinningAxis_BinMode]
    FOREIGN KEY ([BinMode_ID]) REFERENCES [dbo].[BinMode] ([BinMode_ID]);
GO

-- ============================================================
-- 3. Alter ValueBin: make bounds nullable, add NominalValue
-- ============================================================
ALTER TABLE [dbo].[ValueBin]
    DROP CONSTRAINT [CK_ValueBin_Bounds];
GO

ALTER TABLE [dbo].[ValueBin]
    ALTER COLUMN [LowerBound] FLOAT NULL;
GO

ALTER TABLE [dbo].[ValueBin]
    ALTER COLUMN [UpperBound] FLOAT NULL;
GO

ALTER TABLE [dbo].[ValueBin]
    ADD [NominalValue] FLOAT NULL;
GO

ALTER TABLE [dbo].[ValueBin]
    ADD CONSTRAINT [CK_ValueBin_BinValues] CHECK (
        (LowerBound IS NULL) = (UpperBound IS NULL)
        AND (LowerBound IS NULL OR UpperBound > LowerBound)
        AND (NominalValue IS NOT NULL OR LowerBound IS NOT NULL)
    );
GO
