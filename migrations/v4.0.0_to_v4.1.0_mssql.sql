-- Migration: v4.0.0 → v4.1.0
-- Adds SI conversion columns to Unit, ValueKind_ID + QUDT IRI to Parameter,
-- and creates ParameterHasUnit junction table.

ALTER TABLE [dbo].[Unit] ADD [SI_Multiplier] FLOAT NULL;
ALTER TABLE [dbo].[Unit] ADD [SI_Offset]     FLOAT NULL;

ALTER TABLE [dbo].[Parameter] ADD [ValueKind_ID] INT NOT NULL DEFAULT 1;
ALTER TABLE [dbo].[Parameter]
    ADD CONSTRAINT [FK_Parameter_ValueKind]
    FOREIGN KEY ([ValueKind_ID]) REFERENCES [dbo].[ValueKind] ([ValueKind_ID]);

ALTER TABLE [dbo].[Parameter] ADD [QUDT_QuantityKind_IRI] NVARCHAR(256) NULL;

CREATE TABLE [dbo].[ParameterHasUnit] (
    [Parameter_ID] INT NOT NULL,
    [Unit_ID]      INT NOT NULL,
    CONSTRAINT [PK_ParameterHasUnit] PRIMARY KEY ([Parameter_ID], [Unit_ID])
);
ALTER TABLE [dbo].[ParameterHasUnit]
    ADD CONSTRAINT [FK_ParameterHasUnit_Parameter]
    FOREIGN KEY ([Parameter_ID]) REFERENCES [dbo].[Parameter] ([Parameter_ID]);
ALTER TABLE [dbo].[ParameterHasUnit]
    ADD CONSTRAINT [FK_ParameterHasUnit_Unit]
    FOREIGN KEY ([Unit_ID]) REFERENCES [dbo].[Unit] ([Unit_ID]);

INSERT INTO [dbo].[SchemaVersion] ([Version], [AppliedDateTime], [Description], [MigrationScript])
VALUES ('4.1.0', SYSUTCDATETIME(), 'Add SI conversion columns, ValueKind_ID, QUDT IRI, ParameterHasUnit junction table', 'v4.0.0_to_v4.1.0_mssql.sql');
GO
