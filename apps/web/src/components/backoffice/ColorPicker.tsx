import { COLORS, swatchBackground } from "../../lib/colors";

/** Pick a colour from the palette, or type any other name (e.g. "Pista"). */
export default function ColorPicker({ value, onChange, id = "variant-color" }: {
  value: string; onChange: (name: string) => void; id?: string;
}) {
  return (
    <div>
      <div className="mb-2 flex flex-wrap gap-1.5" role="radiogroup" aria-label="Colour">
        {COLORS.map((c) => {
          const selected = value.trim().toLowerCase() === c.name.toLowerCase();
          return (
            <button key={c.name} type="button" role="radio" aria-checked={selected} title={c.name} aria-label={c.name}
              onClick={() => onChange(c.name)}
              className={`h-8 w-8 rounded-full border border-gray-300 transition ${selected ? "ring-2 ring-[#111111] ring-offset-2" : "hover:scale-110"}`}
              style={{ background: swatchBackground(c.name) }} />
          );
        })}
      </div>
      <div className="flex items-center gap-2">
        <span aria-hidden="true" className="h-8 w-8 shrink-0 rounded-full border border-gray-300" style={{ background: swatchBackground(value) }} />
        <input id={id} type="text" required maxLength={50} value={value} onChange={(e) => onChange(e.target.value)}
          placeholder="Choose above or type a colour name"
          className="min-h-10 w-full rounded-lg border border-gray-300 px-3 text-sm outline-none focus:border-[#111111]" />
      </div>
    </div>
  );
}
