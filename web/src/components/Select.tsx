// One control for a choice from a short list, in the month picker's clothes: the same trigger, the same popover, the
// chosen item filled in blue. Keyboard and screen readers get a real menu.
import * as Dropdown from "@radix-ui/react-dropdown-menu";
import { ChevronDown } from "./Icons";

type Option = { value: string; label: string };
type Props = { label: string; value: string; options: Option[]; onChange: (v: string) => void; disabled?: boolean };

export function Select({ label, value, options, onChange, disabled }: Props) {
  const current = options.find((o) => o.value === value)?.label ?? value;
  return (
    <Dropdown.Root modal={false}>
      <Dropdown.Trigger asChild>
        <button type="button" aria-label={`${label}: ${current}`} disabled={disabled}
          className="inline-flex h-[34px] items-center gap-2 whitespace-nowrap rounded-md border border-line bg-white px-3 text-sm font-medium text-ink hover:border-grey focus:outline-none focus:ring-2 focus:ring-tint-line disabled:bg-surface disabled:text-grey">
          {current}<ChevronDown width={14} height={14} className="text-ink-2" />
        </button>
      </Dropdown.Trigger>
      <Dropdown.Portal>
        <Dropdown.Content align="start" sideOffset={6} aria-label={label} className="z-30 min-w-[var(--radix-dropdown-menu-trigger-width)] rounded-xl border border-line bg-white p-1.5 shadow-xl">
          <Dropdown.RadioGroup value={value} onValueChange={onChange}>
            {options.map((o) => (
              <Dropdown.RadioItem key={o.value} value={o.value}
                className={`flex h-9 cursor-pointer items-center rounded-lg px-3 text-sm font-medium outline-none ${o.value === value ? "bg-blue font-semibold text-white" : "text-ink data-[highlighted]:bg-surface"}`}>
                {o.label}
              </Dropdown.RadioItem>
            ))}
          </Dropdown.RadioGroup>
        </Dropdown.Content>
      </Dropdown.Portal>
    </Dropdown.Root>
  );
}
