#!/usr/bin/env python3
"""Generate sample invoice images for testing."""
from PIL import Image, ImageDraw, ImageFont
import random
from datetime import datetime, timedelta
import os

def create_sample_invoice(filename, vendor_name, invoice_num, amount):
    """Create a simple invoice image."""
    # Create white image
    img = Image.new('RGB', (800, 1000), color='white')
    draw = ImageDraw.Draw(img)

    # Use default font
    try:
        font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 32)
        font_medium = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
    except:
        font_large = ImageFont.load_default()
        font_medium = ImageFont.load_default()
        font_small = ImageFont.load_default()

    # Header
    draw.text((50, 50), vendor_name, fill='black', font=font_large)
    draw.text((50, 100), "INVOICE", fill='black', font=font_medium)

    # Invoice details
    y_pos = 200
    draw.text((50, y_pos), f"Invoice #: {invoice_num}", fill='black', font=font_medium)
    y_pos += 50

    date = datetime.now() - timedelta(days=random.randint(1, 30))
    draw.text((50, y_pos), f"Date: {date.strftime('%Y-%m-%d')}", fill='black', font=font_medium)
    y_pos += 50

    draw.text((50, y_pos), f"Due Date: {(date + timedelta(days=30)).strftime('%Y-%m-%d')}", 
              fill='black', font=font_medium)
    y_pos += 100

    # Line items header
    draw.line((50, y_pos, 750, y_pos), fill='black', width=2)
    y_pos += 20
    draw.text((50, y_pos), "Description", fill='black', font=font_medium)
    draw.text((400, y_pos), "Qty", fill='black', font=font_medium)
    draw.text((500, y_pos), "Price", fill='black', font=font_medium)
    draw.text((650, y_pos), "Total", fill='black', font=font_medium)
    y_pos += 40

    # Sample line items
    items = [
        ("Consulting Services", 10, 100.00),
        ("Software License", 2, 250.00),
        ("Support Contract", 1, 500.00),
    ]

    subtotal = 0
    for desc, qty, price in items:
        total = qty * price
        subtotal += total
        draw.text((50, y_pos), desc, fill='black', font=font_small)
        draw.text((400, y_pos), str(qty), fill='black', font=font_small)
        draw.text((500, y_pos), f"${price:.2f}", fill='black', font=font_small)
        draw.text((650, y_pos), f"${total:.2f}", fill='black', font=font_small)
        y_pos += 30

    # Totals
    y_pos += 50
    draw.line((50, y_pos, 750, y_pos), fill='black', width=2)
    y_pos += 20

    tax = subtotal * 0.10
    total = subtotal + tax

    draw.text((450, y_pos), f"Subtotal: ${subtotal:.2f}", fill='black', font=font_medium)
    y_pos += 40
    draw.text((450, y_pos), f"Tax (10%): ${tax:.2f}", fill='black', font=font_medium)
    y_pos += 40
    draw.text((450, y_pos), f"TOTAL: ${total:.2f}", fill='black', font=font_large)

    # Save
    os.makedirs(os.path.dirname(filename) if os.path.dirname(filename) else '.', exist_ok=True)
    img.save(filename)
    print(f"Created: {filename}")
    return filename

def main():
    """Generate sample invoices."""
    output_dir = "data/invoices"
    os.makedirs(output_dir, exist_ok=True)

    vendors = [
        ("Acme Corporation", "INV-2024-001", 1850.00),
        ("Tech Solutions Inc", "INV-2024-002", 3200.50),
        ("Global Services Ltd", "INV-2024-003", 875.25),
        ("Smart Supplies Co", "INV-2024-004", 12500.00),  # High amount for testing
    ]

    print("📄 Generating sample invoices...")
    for vendor, inv_num, amount in vendors:
        filename = os.path.join(output_dir, f"{inv_num.replace('-', '_')}.png")
        create_sample_invoice(filename, vendor, inv_num, amount)

    print(f"\n✅ Generated {len(vendors)} sample invoices in {output_dir}/")
    print("   Run: python run.py --watch")
    print("   Or:  python run.py --dir data/invoices")

if __name__ == "__main__":
    main()
