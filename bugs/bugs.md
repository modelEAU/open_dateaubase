# Interface

- Sensor ingest: DAS name and Tag fields should not be free text, they should look up the existing values in their respective tables and offer a dropdown.

- Lab analysis ingest should allow one to import data from all possible shapes (Scalar, Vector, Matric, Image). For image uploads, it should be possible to upload a folder of images at a time. In those cases, all images in the folder are considered replicates of the parameter, all attached to the same sample. We should strive to reuse the same UI components between Sensor ingest and lab ingest wherever possible.

- In watershed creation flow: Would be nice if the area was calculated based on the uploaded geoJSON

- For Process Units, it would be nice to rename "Tag" to a better name (Maybe P&ID Tag, or P&ID label)
- The Kinds dropdowns should also show the long-form description of each name because otherwise it is very hard to tell apart some of the options. ALL Kinds dropdowns should share this feature -- a reusable UI component may be usefull here.

- Instead of ending the Site wizard flow by redirecting to the first page, a "Success/Error" summary page should appear. That should be a reusable component used in all wizards.

- Campaign wizard has difficulty placing equipments at sampling locations
    -![alt text](<screen grabs/campaign1.png>) ![alt text](<screen grabs/campaign2.png>) ![alt text](<screen grabs/campaign3.png>) ![alt text](<screen grabs/campaign4.png>) ![alt text](<screen grabs/campaign5.png>) ![alt text](<screen grabs/campaign6.png>) 
    

- Equipment moves fail ![alt text](<screen grabs/change_location.png>) 

- Wiring chages fail ![alt text](<screen grabs/change_wiring.png>)