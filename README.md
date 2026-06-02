# fore-edge_generator
A quick and dirty tool to apply fore-edge images to a PDF in preparation for it being sent to print with
either a press or a print on demand service.

The program takes the otherwise complete PDF output from your DTP package of choice and will apply a
border calculated from slicing the image into the number of sheets in the book. The image is scaled / 
cropped to match the ratio of the book (currently it centers the image on the bottom/top/fore-edge).

As an attempt to provide a proofing tool it also reassembles the sliced image and will output two images
for the bottom, top and fore-edge - the verso and recto of each. The recto should be a mirror of the
verso.

The program tries to centre the image on the trim line, and will fill up to the edge of the bleed and to
the thickness specified within the safety margin. (At least, that's the theory). I chose to leave the 
region outside the bleed unprinted to help reduce ink wastage.

Notes:
This is absolutely provided with no warranty whatsoever. Use it at your own risk.

I have only tested this on Windows 11, do let me know if it has issues on OS X or other platforms (or
y'know, go ahead and fix them ;) ).


