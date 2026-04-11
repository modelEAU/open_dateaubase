-- Seed data for e2e testing of the table_import system
-- This script inserts test equipment, parameters, and units for importing sample data
-- Updated for v2.2.0 schema

-- Insert test units
INSERT INTO Unit (Unit) VALUES ('mg/L');
INSERT INTO Unit (Unit) VALUES ('NTU');
INSERT INTO Unit (Unit) VALUES ('°C');
GO

-- Insert test parameters (Unit_ID lives on Channel, not Parameter)
INSERT INTO Parameter ([Parameter]) VALUES ('Dissolved oxygen');
INSERT INTO Parameter ([Parameter]) VALUES ('Turbidity');
INSERT INTO Parameter ([Parameter]) VALUES ('Temperature');
INSERT INTO Parameter ([Parameter]) VALUES ('SCADA Test Value');
GO

-- Insert test sites (using v2.2.0 column name: Name, not Site_name)
INSERT INTO Site ([Name]) VALUES ('Test Site - Rodtox');
INSERT INTO Site ([Name]) VALUES ('Test Site - Basestation');
INSERT INTO Site ([Name]) VALUES ('Test Site - SCADA');
GO

-- Insert test equipment
INSERT INTO Equipment (Identifier, Site_ID) VALUES ('Rodtox-001', (SELECT Site_ID FROM Site WHERE [Name] = 'Test Site - Rodtox'));
INSERT INTO Equipment (Identifier, Site_ID) VALUES ('Basestation-Turb', (SELECT Site_ID FROM Site WHERE [Name] = 'Test Site - Basestation'));
INSERT INTO Equipment (Identifier, Site_ID) VALUES ('SCADA-Simulator', (SELECT Site_ID FROM Site WHERE [Name] = 'Test Site - SCADA'));
GO

PRINT 'Test data seeded successfully.';
GO
