/** Presentation only. Exact canonical millimeters never receive rounded labels. */
export const fractionDenominators=[16,32,64] as const;

function gcd(a:bigint,b:bigint):bigint{
  while(b){const remainder=a%b;a=b;b=remainder;}
  return a;
}

export function formatMeasurement(mm:string,unit:'in'|'mm',denominator=64):string{
  if(unit==='mm')return `${mm} mm`;
  if(!/^\d+(?:\.\d+)?$/.test(mm)||!fractionDenominators.some(value=>value===denominator)){
    throw new RangeError('Use a canonical nonnegative measurement and supported fraction precision.');
  }
  const [whole,decimal='']=mm.split('.');
  const numerator=BigInt(whole+decimal)*5n;
  const divisor=10n**BigInt(decimal.length)*127n;
  const precision=BigInt(denominator);
  const scaled=numerator*precision;
  let rounded=scaled/divisor;
  const remainder=scaled%divisor;
  // Match the exact, ties-to-even rounding used by the saved PDF formatter.
  if(remainder*2n>divisor||(remainder*2n===divisor&&rounded%2n!==0n))rounded++;
  const exact=rounded*divisor===scaled;
  const common=gcd(rounded,precision);
  const reduced=rounded/common,base=precision/common;
  const integer=reduced/base,fraction=reduced%base;
  const text=fraction?`${integer?integer+' ':''}${fraction}/${base}`:String(integer);
  return `${exact?'':'approx. '}${text} in`;
}

export function formatDualMeasurement(mm:string,unit:'in'|'mm',denominator=64):string{
  return unit==='mm'?`${mm} mm`:`${formatMeasurement(mm,unit,denominator)} (${mm} mm)`;
}
