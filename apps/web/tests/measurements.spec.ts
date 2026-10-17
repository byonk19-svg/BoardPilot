import {test,expect} from '@playwright/test';
import {formatMeasurement,formatDualMeasurement} from '../src/measurements';

for(const [mm,denominator,expected] of [
  ['914.4',64,'36 in'],
  ['25.4',64,'1 in'],
  ['0',64,'0 in'],
  ['878.4',64,'approx. 34 37/64 in'],
  ['18',64,'approx. 45/64 in'],
  ['298.8',16,'approx. 11 3/4 in'],
  ['25.400000000001',64,'approx. 1 in'],
  ['0.1984375',64,'approx. 0 in'],
  ['0.5953125',64,'approx. 1/32 in'],
] as const){
  test(`${mm} mm is displayed as ${expected} at ${denominator}ths`,()=>{
    expect(formatMeasurement(mm,'in',denominator)).toBe(expected);
    expect(formatDualMeasurement(mm,'in',denominator)).toBe(`${expected} (${mm} mm)`);
    expect(formatMeasurement(mm,'mm',denominator)).toBe(`${mm} mm`);
  });
}
