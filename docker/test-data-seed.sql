-- Seed data for e2e testing of the table_import system
-- This script inserts test equipment, parameters, and units for importing sample data

-- Insert test units
INSERT INTO Unit (Unit) VALUES ('mg/L');
INSERT INTO Unit (Unit) VALUES ('NTU');
INSERT INTO Unit (Unit) VALUES ('°C');
GO

-- Insert test parameters
INSERT INTO Parameter (Parameter_name, Unit_ID) VALUES ('Dissolved oxygen', (SELECT Unit_ID FROM Unit WHERE Unit = 'mg/L'));
INSERT INTO Parameter (Parameter_name, Unit_ID) VALUES ('Turbidity', (SELECT Unit_ID FROM Unit WHERE Unit = 'NTU'));
INSERT INTO Parameter (Parameter_name, Unit_ID) VALUES ('Temperature', (SELECT Unit_ID FROM Unit WHERE Unit = '°C'));
INSERT INTO Parameter (Parameter_name, Unit_ID) VALUES ('SCADA Test Value', (SELECT Unit_ID FROM Unit WHERE Unit = 'mg/L'));
GO

-- Insert test site
INSERT INTO Site (Site_name) VALUES ('Test Site - Rodtox');
INSERT INTO Site (Site_name) VALUES ('Test Site - Basestation');
INSERT INTO Site (Site_name) VALUES ('Test Site - SCADA');
GO

-- Insert test equipment
INSERT INTO Equipment (Identifier, Site_ID) VALUES ('Rodtox-001', (SELECT Site_ID FROM Site WHERE Site_name = 'Test Site - Rodtox'));
INSERT INTO Equipment (Identifier, Site_ID) VALUES ('Basestation-Turb', (SELECT Site_ID FROM Site WHERE Site_name = 'Test Site - Basestation'));
INSERT INTO Equipment (Identifier, Site_ID) VALUES ('SCADA-Simulator', (SELECT Site_ID FROM Site WHERE Site_name = 'Test Site - SCADA'));
GO

PRINT 'Test data seeded successfully.';
GO
