import fitz  # PyMuPDF
from PIL import Image, ImageOps
import math
import os
import sys
import time
import io

def get_path(prompt):
    """Handles Windows drag-and-drop paths which often include quotes."""
    path = input(prompt).strip()
    if path.startswith('"') and path.endswith('"'):
        path = path[1:-1]
    return path

def convert_color_profile(img, target_mode):
    """Converts PIL image to match target color mode."""
    if img.mode != target_mode:
        #print(f"Converting image to {target_mode}...")
        return img.convert(target_mode)
    return img

def get_paper_thickness_from_weight(weight_lb):
    """
    Maps paper weight (lb) to average sheet thickness (inches).
    Note: A sheet is 2 pages (recto and verso).
    These align with standard KDP/IngramSpark uncoated book paper.
    """
    thickness_map = {
        50: 0.0045,  # standard 50lb white (~444 PPI)
        55: 0.0049,  # standard 55lb cream (~404 PPI)
        60: 0.0050,  # standard 60lb white (~400 PPI)
        70: 0.0060,  # standard 70lb white (~334 PPI)
        80: 0.0070   # premium 80lb white (~285 PPI)
    }

    if weight_lb in thickness_map:
        return thickness_map[weight_lb]

    return weight_lb * 0.00009

def create_preview(proof_top_r, proof_top_v, proof_bot_r, proof_bot_v, proof_mid_r, proof_mid_v, base_name):
    # Save the flat reassembled proofs
    """
    Generates a flat preview image by reassembling the slices.
    Technically this should match the original image - but will
    be flipped horizontally for the verso pages.

    Add Prompt for proof image generation ***
    """
    sys.stdout.write("\x1b[1A")  # Move cursor up one line
    sys.stdout.write("\x1b[2K")  # Clear the entire line
    sys.stdout.write("\x1b[1A")  # Move cursor up one line
    sys.stdout.write("\x1b[2K")  # Clear the entire line
    print("Saving flat reassembled edge proofs...")
    proof_top_r.save(f"{base_name}_proof_top_recto.png")
    proof_top_v.save(f"{base_name}_proof_top_verso.png")

    proof_bot_r.save(f"{base_name}_proof_bottom_recto.png")
    proof_bot_v.save(f"{base_name}_proof_bottom_verso.png")

    proof_mid_r.save(f"{base_name}_proof_foreedge_recto.png")
    proof_mid_v.save(f"{base_name}_proof_foreedge_verso.png")
    sys.stdout.write("\x1b[1A")  # Move cursor up one line
    sys.stdout.write("\x1b[2K")  # Clear the entire line
    print("Proof images saved successfully.")

def process_book():
    add_overlay_image = False
    graduated_fade_border = False

    print("\n\n--- The Antithesis Press Rapid Fore-Edge Generator ---")
    print("-----------------Release: 2026/08/27------------------")
    print("\n***************************************************************************")
    print("** This script is provided without warranty either expressed or implied. **")
    print("** Antithesis Press assumes no liability for any damage howsoever caused **")
    print("**                      by using this script.                            **")
    print("** Free for commercial and individual use. See Github readme for licence **")
    print("***************************************************************************")
    print("\n**You will require:\n  -An input PDF file\n  -PNG image file(s) for the top, bottom and fore-edge sides\n  -PNG files of approximately the size specified for overlay images")
    print("\n(At some point we may write a version where you can ask it to give you\nthe sizes but at the moment, if you don't know the size, run the script \nand it will tell you eventually.)\n")
    pdf_path = get_path("Type or Drag and drop the input PDF file: ")
    while not os.path.isfile(pdf_path):
        print("File not found.")
        pdf_path = get_path("Type or Drag and drop the input PDF file (e.g., input.pdf): ")
        time.sleep(1)
    out_pdf = get_path("\nType or Drag and drop the output PDF filename (e.g., output.pdf): ")
    if os.path.isfile(out_pdf):
        print("\n****Warning: Output file already exists.")
        overwrite_file = input("Overwrite output PDF file (and any matching previously generated proof images)? (y/n): ")
        if overwrite_file.lower() != "y":
            sys.exit("File already exists, user declined overwrite, exiting")

    """
    Paper weight is used to determine the approximate thickness of the book.
    That's necessary to make sure we scale the supplied images in roughly
    the right ratio.
    """
    # Paper weight prompt
    print("\n\nGathering required print and pdf information:")
    print("*********************************************")
    weight_str = input("\nEnter paper weight in lb (e.g. 50, 55, 60): ").strip()
    try:
        weight_lb = float(weight_str)
    except ValueError:
        print("****Warning: Invalid weight. Defaulting to standard 50 lb.")
        weight_lb = 50.0
    paper_thickness_inches = get_paper_thickness_from_weight(weight_lb)
    print(f"Using sheet thickness: {paper_thickness_inches:.5f} inches for {weight_lb}lb paper.")

    # Open PDF
    doc = fitz.open(pdf_path)
    page_count = len(doc)
    sheets = math.ceil(page_count / 2)
    print(f"\nPDF loaded: {page_count} pages ({sheets} sheets).")

    # Get physical dimensions in points
    pw, ph = doc[0].rect.width, doc[0].rect.height

    # Calculate target widths to fit physical proportions
    top_bot_width = int((pw / 72) / paper_thickness_inches)
    fore_width = int((ph / 72) / paper_thickness_inches)

    """
    The position of the band should be basically the bleed plus the
    safety boundary plus 'a bit' to make sure that there's always a
    little bit printed boundary on the page. This is the most
    best-guess calculation in here.
    """
    # Safety boundary prompt
    print("\nFore-edge Print Border Setup:")
    print("*****************************")
    print("\nNote: Take account of the safety margin in this calculation, the bleed size will be added on (in a moment!)")
    print("\nEnter the thickness of the desired border from PDF trim box to safety boundary")
    safety_input = input("(e.g. '0.177 for inches, or '4.5mm'): ").strip().lower()
    # Check the inputs make sense, and if they don't use defaults.
    if safety_input.endswith('mm'):
        try:
            border_mm = float(safety_input.replace('mm', '').strip())
            BORDER_PTS = border_mm * (72 / 25.4)
        except ValueError:
            print("**** Warning: Invalid metric input. Defaulting to 4.5mm.")
            BORDER_PTS = 4.5 * (72 / 25.4)
    else:
        safety_input = safety_input.replace('"', '').replace('in', '').strip()
        try:
            border_inches = float(safety_input)
            BORDER_PTS = border_inches * 72
        except ValueError:
            print("**** Warning: Invalid input. Defaulting to 0.177 inches.")
            BORDER_PTS = 0.177 * 72

    # Get bleed value
    # ...and check they make sense / use defaults again.
    bleed_value = input("\nEnter bleed size\n(e.g. '0.125' for inches, or '3.175mm'): ").strip().lower()
    if bleed_value.endswith('mm'):
        try:
            bleed_mm = float(bleed_value.replace('mm', '').strip())
            bleed_pts = bleed_mm * (72 / 25.4)
        except ValueError:
            print("**** Warning: Invalid metric input. Defaulting to 3.175mm.")
            bleed_pts = 3.175 * (72 / 25.4)
    else:
        bleed_value = bleed_value.replace('"', '').replace('in', '').strip()
        try:
            bleed_inches = float(bleed_value)
            bleed_pts = bleed_inches * 72
        except ValueError:
            print("**** Warning: Invalid input. Defaulting to 0.125 inches.")
            bleed_pts = 0.125 * 72

    print("\nThe border on the pages can either be faded towards from the page edge\ntoward the center of the page, or it can be solid.")
    while True:
        fade_select = input("\nDo you want a graduated fade? (y/n): ").strip().lower()
        if fade_select in ['y', 'n']:
            break  # Valid input received, exit the loop
    if fade_select == "y":
        graduated_fade_border = True

    print("\nOverlay File Information and Setup")
    print("**********************************")
    print("WARNING: Overlay is currently untested, but graduated borders are okay.")
    print(f"\nTo add an overlayed border you will require top/bottom images that are {pw} points by {bleed_pts} points")
    print(f"and a side image that's {ph} points by {bleed_pts} points")
    print("\nNote: If you use an overlayed image over the foreedge image it applies a graduated fade on the calculated border\nregardless of your previous choice.")
    while True:
        border_select = input("\nOverlay a border over the image generated for foreedge effect? (y/n): ").strip().lower()
        if border_select in ['y', 'n']:
            break  # Valid input received, exit the loop
        if border_select == "y":
            add_overlay_image = True
            graduated_fade_border = True


    print("\nGathering Image Files.")
    print("**********************")
    print("This script stretches the shortest side to match the thickness of the book in pages.\nIt then centers the image and crops the other edges off if necessary.\nTypically we recommend making an image which is one pixel per page minimum.\n")
    # Get each file and check they exist. We don't check they're the right type
    # We probably should, and maybe one day I will
    img_top_path = get_path("\nType / Drag and drop the TOP edge PNG: ")
    while not os.path.isfile(img_top_path):
        print("****Warning: File not found.")
        img_top_path = get_path("Enter / Drag and drop the TOP edge PNG: ")
        time.sleep(1)

    img_bot_path = get_path("\nType / Drag and drop the BOTTOM edge PNG: ")
    while not os.path.isfile(img_bot_path):
        print("****Warning: File not found.")
        img_bot_path = get_path("Enter / Drag and drop the BOTTOM edge PNG: ")
        time.sleep(1)

    img_mid_path = get_path("\nType / Drag and drop the FORE-EDGE/MIDDLE PNG: ")
    while not os.path.isfile(img_mid_path):
        print("****Warning: File not found.")
        img_mid_path = get_path("Enter / Drag and drop the FORE-EDGE/MIDDLE PNG: ")
        time.sleep(1)
    if add_overlay_image:
        img_overlay_top_path = get_path("\nType / Drag and drop the TOP OVERLAY PNG: ")
        while not os.path.isfile(img_overlay_top_path):
            print("****Warning: File not found.")
            img_overlay_top_path = get_path("Type / Drag and drop the TOP OVERLAY PNG: ")
            time.sleep(1)

        img_overlay_bottom_path = get_path("\nType / Drag and drop the BOTTOM OVERLAY PNG: ")
        while not os.path.isfile(img_overlay_bottom_path):
            print("****Warning: File not found.")
            img_overlay_bottom_path= get_path("Type / Drag and drop the BOTTOM OVERLAY PNG: ")
            time.sleep(1)

        img_overlay_middle_path = get_path("\nType / Drag and drop the FORE-EDGE/MIDDLE OVERLAY PNG: ")
        while not os.path.isfile(img_overlay_middle_path):
            print("****Warning: File not found.")
            img_overlay_middle_path = get_path("Type / Drag and drop the FORE-EDGE/MIDDLE OVERLAY PNG: ")
            time.sleep(1)

    # Load Images
    try:
        top_img = Image.open(img_top_path)
        bot_img = Image.open(img_bot_path)
        mid_img = Image.open(img_mid_path)
        if add_overlay_image:
            overlay_top_img = Image.open(img_overlay_top_path)
            overlay_bottom_img = Image.open(img_overlay_bottom_path)
            overlay_middle_img = Image.open(img_overlay_middle_path)

    except Exception as e:
        print(f"****Warning: Error loading images: {e}")
        return

    print("\nProcessing Images and PDF:")
    target_mode = 'RGB'
    print(f"Converting top image to {target_mode}...")
    top_img = convert_color_profile(top_img, target_mode)
    sys.stdout.write("\x1b[1A")  # Move cursor up one line
    sys.stdout.write("\x1b[2K")  # Clear the entire line
    print(f"Converting bottom image to {target_mode}...")
    bot_img = convert_color_profile(bot_img, target_mode)
    sys.stdout.write("\x1b[1A")  # Move cursor up one line
    sys.stdout.write("\x1b[2K")  # Clear the entire line
    print(f"Converting foreedge image to {target_mode}...")
    mid_img = convert_color_profile(mid_img, target_mode)
    if add_overlay_image:
        sys.stdout.write("\x1b[1A")  # Move cursor up one line
        sys.stdout.write("\x1b[2K")  # Clear the entire line
        print(f"Converting overlay top image to {target_mode}...")
        overlay_top_img = convert_color_profile(overlay_top_img, target_mode)
        sys.stdout.write("\x1b[1A")  # Move cursor up one line
        sys.stdout.write("\x1b[2K")  # Clear the entire line
        print(f"Converting bottom bottom image to {target_mode}...")
        overlay_bottom_img = convert_color_profile(overlay_bottom_img, target_mode)
        sys.stdout.write("\x1b[1A")  # Move cursor up one line
        sys.stdout.write("\x1b[2K")  # Clear the entire line
        print(f"Converting overlay middle image to {target_mode}...")
        overlay_middle_img = convert_color_profile(overlay_middle_img, target_mode)

    sys.stdout.write("\x1b[1A")  # Move cursor up one line
    sys.stdout.write("\x1b[2K")  # Clear the entire line
    print("Scaling and cropping images to fit physical book proportions...")
    """
    We scale the image to fit, center, then crop off the edges.
    If you make your images roughly the right ratio of height to
    width you'll probably get better results.

    To print correctly, the top edge and the longest side need to be flipped,
    so we'll do that first.
    """

    top_img = ImageOps.flip(top_img)
    mid_img = ImageOps.flip(mid_img)

    top_img = ImageOps.fit(top_img, (top_bot_width, sheets), method=Image.Resampling.LANCZOS)
    bot_img = ImageOps.fit(bot_img, (top_bot_width, sheets), method=Image.Resampling.LANCZOS)
    mid_img = ImageOps.fit(mid_img, (fore_width, sheets), method=Image.Resampling.LANCZOS)
    # verso_mid_img = ImageOps.flip(mid_img)
    verso_mid_img = mid_img

    base_name = os.path.splitext(out_pdf)[0]

    sys.stdout.write("\x1b[1A")  # Move cursor up one line
    sys.stdout.write("\x1b[2K")  # Clear the entire line
    print("Creating canvases for proof images...")
    # Create blank canvases to verify the final processed output
    # We create a Recto (front) and Verso (back) version for all three edges
    proof_top_r = Image.new(target_mode, (top_img.width, sheets))
    proof_top_v = Image.new(target_mode, (top_img.width, sheets))

    proof_bot_r = Image.new(target_mode, (bot_img.width, sheets))
    proof_bot_v = Image.new(target_mode, (bot_img.width, sheets))

    proof_mid_r = Image.new(target_mode, (mid_img.width, sheets))
    proof_mid_v = Image.new(target_mode, (verso_mid_img.width, sheets))


    """
    Apply fade and overlay if requested.
    """
    im_side="none"
    def linear_gradient(mode='L'):
        # Creates a 1x256 vertical gradient
        # (Use (256, 1) instead if you want a left-to-right horizontal fade)
        gradient = Image.new(mode, (1, 256))
        # Fills the gradient with values from 255 (opaque) down to 0 (transparent)
        gradient.putdata(list(range(255, -1, -1)))
        return gradient

    def fade_to_white(img, orient="none"):
        # temporarily convert to RGBA to add transparency
        width, height = img.size
        #print(f"{width} wide and {height} high")
        img = img.convert('RGBA')
        # Create an appropriately sized white background images
        white_bg = Image.new('RGB', (width, height), (255, 255, 255))
        # Create an appropriately sized linear gradient
        if orient == "top":
            alpha = linear_gradient(mode='L').resize((width, height), resample=Image.Resampling.NEAREST)
        if orient == "bottom":
            alpha = linear_gradient(mode='L').transpose(Image.Transpose.ROTATE_180).resize((width, height), resample=Image.Resampling.NEAREST)
        """ The foredge file is a special little flower that needs to have transparency
        so that it'll blend with the top and bottom borders nicely so we leave it as
        RGB with an alpha channel """
        if orient == "fore":
            alpha = linear_gradient(mode='L').resize((width, height), resample=Image.Resampling.NEAREST)
            white_bg = white_bg.convert('RGBA')
            img.putalpha(alpha)
            return img
        if orient == "v_fore":
            alpha = linear_gradient(mode='L').transpose(Image.Transpose.ROTATE_180).resize((width, height), resample=Image.Resampling.NEAREST)
            white_bg = white_bg.convert('RGBA')
            img.putalpha(alpha)
            return img
        #Apply the alpha channel to the image, then layer the background behind it
        img.putalpha(alpha)
        white_bg.paste(img, (0,0), mask=alpha)
        return white_bg

    def overlay_image (img, im_side):
        width, height = img.size

        if im_side == "top":
            temp_overlay = overlay_top_img.resize((width, height), resample=Image.Resampling.LANCZOS)
            img = Image.blend(img, temp_overlay, alpha=0.5)

        elif im_side == "bottom":
            temp_overlay = overlay_bottom_img.resize((width, height), resample=Image.Resampling.LANCZOS)
            img = Image.blend(img, temp_overlay, alpha=0.5)

        elif im_side in ["fore", "v_fore"]:
            # Corrected variable name: overlay_middle_img
            temp_overlay = overlay_middle_img.resize((width, height), resample=Image.Resampling.LANCZOS)
            img = Image.blend(img, temp_overlay, alpha=0.5)
        return img

    sys.stdout.write("\x1b[1A")  # Move cursor up one line
    sys.stdout.write("\x1b[2K")  # Clear the entire line
    if graduated_fade_border == False:
        print("Generating images and applying each image to safety boundary.\nCurrent page:")
    if graduated_fade_border:
        print("Generating images and adding a graduated fade to each image.\nOnce generated, applying each image to safety boundary.\nCurrent page:")
    if add_overlay_image:
        print("Generating images, then adding a graduated fade and overlay to each image.\nOnce generated, applying each image to safety boundary.\nCurrent page:")

    for i in range(sheets):
        print(f"\r{i}     ", end="", flush=True)
        bot_strip = bot_img.crop((0, i, bot_img.width, i + 1))
        mid_strip = mid_img.crop((0, i, mid_img.width, i + 1))
        top_strip = top_img.crop((0, i, top_img.width, i + 1))
        verso_mid_strip = mid_strip

        all_strips_height_width = bleed_pts + BORDER_PTS

        # Generate Scaled Images
        # Generate Scaled Images using .resize() instead of ImageOps.fit
        stretched_top_img = top_strip.resize((int(top_strip.width), int(all_strips_height_width)), resample=Image.Resampling.LANCZOS)
        stretched_bottom_img = bot_strip.resize((int(bot_strip.width), int(all_strips_height_width)), resample=Image.Resampling.LANCZOS)
        stretched_mid_img = mid_strip.resize((int(mid_strip.width), int(all_strips_height_width)), resample=Image.Resampling.LANCZOS)
        stretched_verso_mid = stretched_mid_img

        # Add fade and overlay
        if graduated_fade_border:
            #print("\nAlso adding a graduated fade to each image.")
            stretched_top_img = fade_to_white(stretched_top_img, "top")
            stretched_bottom_img = fade_to_white(stretched_bottom_img, "bottom")
            stretched_mid_img = fade_to_white(stretched_mid_img, "fore")
            stretched_verso_mid = fade_to_white(stretched_verso_mid, "v_fore")
        if add_overlay_image:
            #print("\nAnd adding the overlay.")
            stretched_top_img = overlay_image(stretched_top_img, "top")
            stretched_bottom_img = overlay_image (stretched_bottom_img, "bottom")
            stretched_mid_img = overlay_image (stretched_mid_img, "fore")
            stretched_mid_img = overlay_image (stretched_verso_mid, "v_fore")

        """
        Create Proof images: Each individual slice is reassembled back into a single image.
        """
        # Recto
        proof_top_r.paste(top_strip, (0, i))
        proof_bot_r.paste(bot_strip, (0, i))
        proof_mid_r.paste(mid_strip, (0, i))
        #Verso
        proof_top_v.paste(top_strip.transpose(Image.FLIP_LEFT_RIGHT), (0, i))
        proof_bot_v.paste(bot_strip.transpose(Image.FLIP_LEFT_RIGHT), (0, i))
        proof_mid_v.paste(verso_mid_strip.transpose(Image.FLIP_LEFT_RIGHT), (0,i))


        """
        Turns the image into bytes with appropriate mirroring and
        rotation for the PDF.
        """
        def img_to_bytes(img, mirror=False, rotate=False):
            if mirror:
                img = img.transpose(Image.FLIP_LEFT_RIGHT)
            if rotate:
                img = img.rotate(-90, expand=True)
            b = io.BytesIO()
            img.save(b, format="PNG" if target_mode == 'RGB' else "JPEG")
            return b.getvalue()


        """
        This took some experimentation to get right! We use the trimbox rather than
        the PDF edges because those seemed to vary despite sample files having a
        consistent bleed and safety margin. So instead here we're calculating the
        position of the bands based off the trimbox +/- both the safety margin and
        the bleed.

        We're trying to avoid just wasting ink by printing outside that area.

        The variable naming in this section could do with tidying up because it's
        taken a few stabs at how this should work to get it working, so, uh, soz.
        """
        def get_aligned_rect(page, side, border_pts):
            trim = page
            if side == "top":
                return fitz.Rect(trim.x0, trim.y0 - bleed_pts, trim.x1, trim.y0 + border_pts)
            elif side == "bottom":
                return fitz.Rect(trim.x0, trim.y1 - border_pts, trim.x1, trim.y1 + bleed_pts)
            elif side == "fore":
                # For fore-edge recto, we align to the far edge of the trim box
                return fitz.Rect(trim.x1 - border_pts, trim.y0, trim.x1 + bleed_pts, trim.y1)
            elif side == "verso_fore":
                #return fitz.Rect(v_trim.x0 - bleed_pts, v_trim.y0, v_trim.x0 + BORDER_PTS, v_trim.y1)
                return fitz.Rect(trim.x0 - bleed_pts, trim.y0, trim.x0 + border_pts, trim.y1)
            #elif side == "fore_v":
                # For fore-edge verso, we align to the near edge of the trim box
                # return fitz.Rect(trim.x1 - bleed_pts, trim.y0, trim.x1 + border_pts, trim.y1)
            return None


        # Front of sheet (Recto)
        recto_idx = i * 2
        if recto_idx < page_count:
            page = doc[recto_idx]
            r_trim = page.trimbox

            page.insert_image(get_aligned_rect(r_trim, "top", BORDER_PTS), stream=img_to_bytes(stretched_top_img), keep_proportion=False)
            page.insert_image(get_aligned_rect(r_trim, "bottom", BORDER_PTS), stream=img_to_bytes(stretched_bottom_img), keep_proportion=False)
            page.insert_image(get_aligned_rect(r_trim, "fore", BORDER_PTS), stream=img_to_bytes(stretched_mid_img, rotate=True), keep_proportion=False)

        # Back of sheet (Verso)
        verso_idx = i * 2 + 1
        if verso_idx < page_count:
            page = doc[verso_idx]

            # Again, changed to use trim box for hopefully better alignment
            # Verso fore-edge is on the left side of the trim box
            v_trim = page.trimbox

            verso_fore = fitz.Rect(v_trim.x0 - bleed_pts, v_trim.y0, v_trim.x0 + BORDER_PTS, v_trim.y1)

            page.insert_image(get_aligned_rect(v_trim, "top", BORDER_PTS), stream=img_to_bytes(stretched_top_img, mirror=True), keep_proportion=False)
            page.insert_image(get_aligned_rect(v_trim, "bottom", BORDER_PTS), stream=img_to_bytes(stretched_bottom_img, mirror=True), keep_proportion=False)
            page.insert_image(get_aligned_rect(v_trim, "verso_fore", BORDER_PTS), stream=img_to_bytes(stretched_verso_mid, mirror=True, rotate=True), keep_proportion=False)

    create_preview(proof_top_r, proof_top_v, proof_bot_r, proof_bot_v, proof_mid_r, proof_mid_v, base_name)

    print(f"Saving final PDF to {out_pdf}...")
    doc.save(out_pdf, garbage=4, deflate=True)
    doc.close()
    print("Done!")

if __name__ == "__main__":
    process_book()
