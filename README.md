# fore-edge_generator

A quick and dirty tool to apply fore-edge images to a PDF in preparation for it being sent to print with
either a press or a print on demand service.

The program takes the otherwise complete PDF output from your DTP package of choice and will apply a
border calculated from slicing the image into the number of sheets in the book. That 1 pixel wide slice
is then stretched to make the border and flipped so that the verso/recto sides of the page should match
and should align. The supplied image(s) is(are) scaled / cropped to match the aspect ratio of the edges 
of the book (currently it centers the image on the bottom/top/fore-edge and crops the sides off if
necessary).

It has some marginal checking to try not to immediately overwrite things you might care about.

As an attempt to provide a proofing tool it also reassembles the sliced image and will output two images
for the bottom, top and fore-edge - the verso and recto of each. The recto should be a mirror of the
verso.

The program tries to centre the image on the trim line, and will fill up to the edge of the bleed and to
the thickness specified within the safety margin. (At least, that's the theory). I chose to leave the 
region outside the bleed unprinted to help reduce ink wastage.

Notes:
This is absolutely provided with no warranty whatsoever. Use it at your own risk.

It will absolutely overwrite any contents in that print area.

I have only tested this on Windows 11, do let me know if it has issues on OS X or other platforms (or
y'know, go ahead and fix them ;) ).


