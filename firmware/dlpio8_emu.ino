/*
 * DLP-IO8 compatible data acquisition on Arduino
 * This code is placed in the public domain by its author, Ian Harvey.
 */

#include <OneWire.h>

void setup()
{ 
  Serial.begin(115200); 
  while (!Serial)
    ; // wait for serial port to connect. Needed for Leonardo only

  analogReference(INTERNAL);
  
  //Serial.println("RESET");
} 


void printWidth(unsigned val, byte width)
{
  unsigned n=1;
  while (width-- > 1)
    n *= 10;
  // n is now the smallest value which fills 'width' digits
  while ( val < n )
  {
    Serial.write('0');
    n = n/10;
  }
  if ( val > 0 )
    Serial.print(val);
}


// Analogue input --------------------------


static const byte MAX_ADC_CHANS = 6;

void readVin(byte chan)
{
  int val = (chan < MAX_ADC_CHANS) ? analogRead(chan) : 0;
  // Map 0-1023 onto 0 to 1.101V output
  int mV = val + (val >> 4) + (val >> 6);
  printWidth( mV/1000, 1 );
  Serial.write( '.' );
  printWidth( mV % 1000, 3 );
  Serial.print( "V\n\r" );
}

// DS18B20 temperature input -------------

const byte MAX_TEMP_CHANS = 4;

OneWire tempCh1(13);
OneWire tempCh2(12);
OneWire tempCh3(11);
OneWire tempCh4(10);

OneWire *tempChans[MAX_TEMP_CHANS] = 
{ &tempCh1, &tempCh2, &tempCh3, &tempCh4 };

void readTemp(unsigned chan)
{
  OneWire *ds;
  byte i;
  byte buf[10];
  unsigned int tempReg;

  if ( chan >= MAX_TEMP_CHANS ) {
    goto fail_exit;
  }
  ds = tempChans[chan];
  
  if ( !ds->reset() )
  {
    //Serial.print("<not present>");
    goto fail_exit;
  }
  
  ds->write(0x33); // READ ROM
  for (i=0; i < 8; i++ )
    buf[i] = ds->read();
    
  ds->reset();
  ds->select(buf);
  ds->write(0x44,1);         // start conversion, with parasite power on at the end
  
  delay(1000);     // maybe 750ms is enough, maybe not
  // we might do a ds.depower() here, but the reset will take care of it.
  
  ds->reset();
  ds->select(buf);    
  ds->write(0xBE);         // Read Scratchpad

  for ( i = 0; i < 9; i++) {           // we need 9 bytes
    buf[i] = ds->read();
  }
  if ( buf[8] != OneWire::crc8(buf, 8) )
  {
    //Serial.print("<CRC mismatch>");
    goto fail_exit;
  }

  tempReg = (buf[1] << 8) | buf[0];
  if (tempReg & 0x8000)
  {
    Serial.write('-');
    tempReg = (~tempReg) + 1;
  }
  printWidth( tempReg >> 4, 3 );
  Serial.print('.');
  printWidth( ((tempReg & 0xF) * 100) >> 4, 2 );
  Serial.write(0xF8);
  Serial.print("C\n\r");
  return;
  
fail_exit:
  Serial.print("999.9");
  Serial.write(0xF8);
  Serial.print("C\n\r");
}

void loop()
{ 
  if (Serial.available() <= 0)
    return;
    
  unsigned in = Serial.read();
  switch(in)
  {
    case '\'':
      Serial.write("Q");
      break;
    
    case 'Z':  readVin(0);  break;
    case 'X':  readVin(1);  break;
    case 'C':  readVin(2);  break;
    case 'V':  readVin(3);  break;
    case 'B':  readVin(4);  break;
    case 'N':  readVin(5);  break;
    case 'M':  readVin(6);  break;
    case ',':  readVin(7);  break;
    
    case '9':  readTemp(0);  break;
    case '0':  readTemp(1);  break;
    case '-':  readTemp(2);  break;
    case '=':  readTemp(3);  break;
    case 'O':  readTemp(4);  break;
    case 'P':  readTemp(5);  break;
    case '[':  readTemp(6);  break;
    case ']':  readTemp(7);  break;
    
    case ';':  break; // Set Temp in deg C - ignored
    default:
      Serial.write(in);
      Serial.write("??");
      break;
  }
} 

