-- Rollback: v4.1.0 → v4.0.0

ALTER TABLE [dbo].[ParameterHasUnit] DROP CONSTRAINT [FK_ParameterHasUnit_Unit];
ALTER TABLE [dbo].[ParameterHasUnit] DROP CONSTRAINT [FK_ParameterHasUnit_Parameter];
DROP TABLE [dbo].[ParameterHasUnit];

ALTER TABLE [dbo].[Parameter] DROP COLUMN [QUDT_QuantityKind_IRI];
ALTER TABLE [dbo].[Parameter] DROP CONSTRAINT [FK_Parameter_ValueKind];
ALTER TABLE [dbo].[Parameter] DROP COLUMN [ValueKind_ID];

ALTER TABLE [dbo].[Unit] DROP COLUMN [SI_Offset];
ALTER TABLE [dbo].[Unit] DROP COLUMN [SI_Multiplier];
