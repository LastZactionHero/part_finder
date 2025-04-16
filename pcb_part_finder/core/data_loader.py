"""Module for loading input data files."""

import csv
import os
from typing import List, Dict, Any
from pcb_part_finder.llm_handler import get_llm_response

class DataLoaderError(Exception):
    """Custom exception for data loading errors."""
    pass

# Hard-coded ideal BOM format
IDEAL_BOM_FORMAT = """Qty,Description,Possible MPN,Package,Notes/Source
1,"ESP32 Wi-Fi/BT Module, 8MB Flash, 2MB PSRAM",ESP32-WROOM-32E-N8R2,RF_Module:ESP32-WROOM-32E,"Sufficient for MP3, SMT. Use Espressif KiCad Lib. Verify footprint."
1,"USB Type-C Receptacle, 2.0, 16-pin, Horiz, SMT w/ posts",UJ20-C-H-G-SMT-4-P16-TR,Connector_USB:USB_C_Receptacle_...,"SameSky, 5A, 48V. Find/verify footprint."
1,USB-to-UART Bridge,CP2102N-A02-GQFN24,Package_DFN_QFN:QFN-24-1EP_...,"Silicon Labs, Integrated Osc.. Find/verify footprint."
1,"LDO Voltage Regulator, 3.3V, 1A",AMS1117-3.3,Package_TO_SOT_SMD:SOT-223-3,"Common LDO, requires caps."
2,NPN Transistor (Small Signal),BC547 / 2N3904,Package_TO_SOT_THT:TO-92_Inline,For auto-reset circuit. (Or 2N7002DW SOT363 ).
1,LED Green 3mm THT,,LED_THT:LED_D3.0mm,Power indicator.
1,LED Blue 3mm THT,,LED_THT:LED_D3.0mm,"User blink LED (e.g., on GPIO2)."
4,Resistor 10kΩ,,Resistor_SMD:R_0805_2012Metric,"Pull-ups (EN, GPIO0), Pull-downs (GPIO12, GPIO15 - adjust as needed)."
1,Resistor 1kΩ,,Resistor_SMD:R_0805_2012Metric,CP2102N RSTb pull-up.
2,Resistor ~330Ω (TBD),,Resistor_SMD:R_0805_2012Metric,LED Current Limiting. Value depends on LED Vf.
2,Resistor 1kΩ-10kΩ (TBD),,Resistor_SMD:R_0805_2012Metric,Auto-reset transistor base resistors (if using BJTs).
2,Capacitor 10µF Ceramic,,Capacitor_SMD:C_0805_2012Metric,"Bulk capacitance (LDO in, ESP32 3V3)."
1,Capacitor 22µF Tantalum (or Ceramic),,Capacitor_SMD:CP_Elec_...,LDO Output Stability. Check LDO datasheet.
1,Capacitor 1µF Ceramic,,Capacitor_SMD:C_0805_2012Metric,ESP32 EN pin RC delay.
~6,Capacitor 0.1µF Ceramic,,Capacitor_SMD:C_0603_1608Metric,"Decoupling (ESP32, CP2102N). Place close to IC pins."
1,Capacitor 4.7µF Ceramic,,Capacitor_SMD:C_0805_2012Metric,CP2102N VREGIN decoupling.
2,Push Button Switch Tactile,,Button_Switch_THT:SW_PUSH_...,Manual Reset (EN) and Boot (GPIO0).
~4,"Pin Header Male 0.1"" Pitch (Various Sizes)",,Connector_PinHeader_2.54mm:...,GPIO breakout."""

def reformat_csv_with_llm(malformed_csv_path: str) -> str:
    """Reformat a CSV using the LLM.
    
    Args:
        malformed_csv_path: Path to the input CSV file
        
    Returns:
        Path to the reformatted CSV file
        
    Raises:
        DataLoaderError: If the reformatting fails
    """
    try:
        # Read the input CSV content
        with open(malformed_csv_path, 'r', encoding='utf-8') as f:
            input_content = f.read()
            
        # Create prompt for the LLM
        prompt = f"""You are a helpful assistant that reformats CSV files. I have an input CSV file and an ideal CSV format. 
Please reformat the input CSV to match the structure of the ideal CSV as closely as possible.

The ideal CSV format is:
{IDEAL_BOM_FORMAT}

The input CSV content is:
{input_content}

Please reformat the input CSV to match the structure of the ideal CSV. The output should be a valid CSV with the same columns as the ideal CSV.
If some information is missing or unclear, make your best guess based on the context.
Return ONLY the reformatted CSV content, nothing else."""

        # Get reformatted content from LLM
        reformatted_content = get_llm_response(prompt)
        if not reformatted_content:
            raise DataLoaderError("LLM failed to reformat CSV")
            
        # Save reformatted content to a new file
        reformatted_path = os.path.splitext(malformed_csv_path)[0] + "_reformatted.csv"
        with open(reformatted_path, 'w', encoding='utf-8') as f:
            f.write(reformatted_content)
            
        return reformatted_path
        
    except Exception as e:
        raise DataLoaderError(f"Error reformatting CSV with LLM: {e}")

def load_input_csv(filepath: str) -> List[Dict[str, Any]]:
    """Load the input CSV file.
    
    Args:
        filepath: Path to the input CSV file.
        
    Returns:
        A list of dictionaries, where each dictionary represents a row from the CSV.
        
    Raises:
        DataLoaderError: If the file cannot be read or is not a valid CSV.
    """
    try:
        # Always reformat the CSV using the LLM
        reformatted_path = reformat_csv_with_llm(filepath)
        
        # Load the reformatted CSV
        with open(reformatted_path, 'r', encoding='utf-8') as f:
            # Try to read the first line to check for header
            first_line = f.readline().strip()
            if not first_line:
                raise DataLoaderError("CSV file is empty")
            
            # Check for expected headers
            expected_headers = {"Qty", "Description", "Possible MPN", "Package", "Notes/Source"}
            headers = set(h.strip() for h in first_line.split(','))
            if not expected_headers.issubset(headers):
                missing = expected_headers - headers
                raise DataLoaderError(f"CSV is missing required headers: {', '.join(missing)}")
            
            # Reset file pointer and read the CSV
            f.seek(0)
            reader = csv.DictReader(f)
            try:
                return list(reader)
            except csv.Error as e:
                raise DataLoaderError(f"Error parsing CSV content: {e}")
                
    except (FileNotFoundError, IOError) as e:
        raise DataLoaderError(f"Error loading input CSV: {e}")
    except csv.Error as e:
        raise DataLoaderError(f"Error parsing CSV: {e}")
    except Exception as e:
        raise DataLoaderError(f"Error processing CSV: {e}") 