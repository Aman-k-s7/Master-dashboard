import { useEffect, useMemo, useState } from "react";
import { format } from "date-fns";
import { CalendarIcon, ChevronDown, Filter, RotateCcw, Search } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Calendar } from "@/components/ui/calendar";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import type { DashboardFilters, FilterOptions } from "@/lib/dashboard";
import { getDeviceDisplayName } from "@/lib/dashboard";


interface DropdownOption {
  label: string;
  value: string;
}

interface MultiSelectDropdownProps {
  label: string;
  placeholder: string;
  options: DropdownOption[];
  selected: string[];
  onChange: (selected: string[]) => void;
  searchPlaceholder?: string;
  enableSearch?: boolean;
}


function MultiSelectDropdown({
  label,
  placeholder,
  options,
  selected,
  onChange,
  searchPlaceholder = "Search...",
  enableSearch = false,
}: MultiSelectDropdownProps) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const allSelected = options.length > 0 && selected.length === options.length;

  const filteredOptions = useMemo(() => {
    const query = search.trim().toLowerCase();
    if (!query) return options;
    return options.filter((option) => option.label.toLowerCase().includes(query));
  }, [options, search]);

  const toggleAll = () => {
    onChange(allSelected ? [] : options.map((option) => option.value));
  };

  const toggle = (optionValue: string) => {
    onChange(
      selected.includes(optionValue)
        ? selected.filter((item) => item !== optionValue)
        : [...selected, optionValue],
    );
  };

  const triggerText = selected.length === 0
    ? placeholder
    : allSelected
      ? `All ${label.toLowerCase()}`
      : `${selected.length} selected`;

  return (
    <Popover
      open={open}
      onOpenChange={(nextOpen) => {
        setOpen(nextOpen);
        if (!nextOpen) setSearch("");
      }}
    >
      <PopoverTrigger asChild>
        <button className="w-full flex items-center justify-between px-3 py-2 text-sm border border-border rounded bg-card text-foreground hover:bg-muted/50 transition-colors">
          <span className={`truncate text-left ${selected.length === 0 ? "text-muted-foreground" : "text-foreground"}`}>
            {triggerText}
          </span>
          <ChevronDown className="h-3.5 w-3.5 shrink-0 opacity-50" />
        </button>
      </PopoverTrigger>
      <PopoverContent className="w-64 p-2" align="start">
        {enableSearch ? (
          <div className="relative mb-2">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder={searchPlaceholder}
              className="h-9 pl-8 text-sm"
            />
          </div>
        ) : null}

        <label className="flex items-center gap-2 px-2 py-1.5 text-sm cursor-pointer hover:bg-muted rounded">
          <Checkbox checked={allSelected} onCheckedChange={toggleAll} />
          <span className="font-medium">Select all</span>
        </label>
        <div className="h-px bg-border my-1" />
        <div className="max-h-56 overflow-y-auto">
          {filteredOptions.length ? (
            filteredOptions.map((option) => (
              <label key={option.value} className="flex items-center gap-2 px-2 py-1.5 text-sm cursor-pointer hover:bg-muted rounded">
                <Checkbox checked={selected.includes(option.value)} onCheckedChange={() => toggle(option.value)} />
                <span>{option.label}</span>
              </label>
            ))
          ) : (
            <p className="px-2 py-3 text-sm text-muted-foreground">No matching {label.toLowerCase()} found.</p>
          )}
        </div>
      </PopoverContent>
    </Popover>
  );
}


interface FilterSidebarProps {
  options?: FilterOptions;
  onApply: (filters: DashboardFilters) => void;
}


export default function FilterSidebar({ options, onApply }: FilterSidebarProps) {
  const [dateFrom, setDateFrom] = useState<Date | undefined>();
  const [dateTo, setDateTo] = useState<Date | undefined>();
  const [devices, setDevices] = useState<string[]>([]);
  const [meals, setMeals] = useState<string[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [wasteTypes, setWasteTypes] = useState<string[]>([]);
  const [weeks, setWeeks] = useState<string[]>([]);

  useEffect(() => {
    if (!options) return;
    setDateFrom(options.min_date ? new Date(options.min_date) : undefined);
    setDateTo(options.max_date ? new Date(options.max_date) : undefined);
    setDevices(options.devices);
    setMeals(options.meal_types);
    setCategories(options.categories);
    setWasteTypes(options.waste_types ?? []);
    setWeeks([]);
  }, [options]);

  const deviceOptions = useMemo<DropdownOption[]>(() => (options?.devices ?? []).map((item) => ({ label: getDeviceDisplayName(item), value: item })), [options?.devices]);
  const mealOptions = useMemo<DropdownOption[]>(() => (options?.meal_types ?? []).map((item) => ({ label: item, value: item })), [options?.meal_types]);
  const categoryOptions = useMemo<DropdownOption[]>(() => (options?.categories ?? []).map((item) => ({ label: item, value: item })), [options?.categories]);
  const wasteTypeOptions = useMemo<DropdownOption[]>(() => (options?.waste_types ?? []).map((item) => ({ label: item, value: item })), [options?.waste_types]);
  const weekOptions = useMemo<DropdownOption[]>(() => (options?.weeks ?? []).map((item) => ({ label: item.label, value: item.value })), [options?.weeks]);

  const apply = () => {
    let finalDateFrom = dateFrom ? format(dateFrom, "yyyy-MM-dd") : undefined;
    let finalDateTo = dateTo ? format(dateTo, "yyyy-MM-dd") : undefined;
    if (weeks.length && options?.weeks?.length) {
      const selected = options.weeks.filter((item) => weeks.includes(item.value));
      if (selected.length) {
        const sorted = selected
          .map((item) => ({ start: item.start_date, end: item.end_date }))
          .sort((a, b) => a.start.localeCompare(b.start));
        finalDateFrom = sorted[0].start;
        finalDateTo = sorted[sorted.length - 1].end;
      }
    }
    onApply({
      dateFrom: finalDateFrom,
      dateTo: finalDateTo,
      devices,
      mealTypes: meals,
      categories,
      wasteTypes,
      weeks,
    });
  };

  const reset = () => {
    setDateFrom(options?.min_date ? new Date(options.min_date) : undefined);
    setDateTo(options?.max_date ? new Date(options.max_date) : undefined);
    setDevices(options?.devices ?? []);
    setMeals(options?.meal_types ?? []);
    setCategories(options?.categories ?? []);
    setWasteTypes(options?.waste_types ?? []);
    setWeeks([]);
    onApply({
      dateFrom: options?.min_date ?? undefined,
      dateTo: options?.max_date ?? undefined,
      devices: options?.devices ?? [],
      mealTypes: options?.meal_types ?? [],
      categories: options?.categories ?? [],
      wasteTypes: options?.waste_types ?? [],
      weeks: [],
    });
  };

  return (
    <aside className="w-64 shrink-0 bg-card border-r border-border h-screen sticky top-0 flex flex-col">
      <div className="px-4 py-4 border-b border-border">
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-primary" />
          <span className="text-sm font-semibold text-foreground">Filters</span>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-4">
        <div>
          <label className="text-xs font-medium text-muted-foreground mb-1.5 block">Date Range</label>
          <div className="space-y-1.5">
            <Popover>
              <PopoverTrigger asChild>
                <button className="w-full flex items-center justify-between px-3 py-2 text-sm border border-border rounded bg-card text-foreground hover:bg-muted/50 transition-colors">
                  <span className={dateFrom ? "text-foreground" : "text-muted-foreground"}>{dateFrom ? format(dateFrom, "MMM d, yyyy") : "Select start date"}</span>
                  <CalendarIcon className="h-3.5 w-3.5 opacity-50" />
                </button>
              </PopoverTrigger>
              <PopoverContent className="w-auto p-0" align="start">
                <Calendar mode="single" selected={dateFrom} onSelect={setDateFrom} className="p-3 pointer-events-auto" />
              </PopoverContent>
            </Popover>
            <Popover>
              <PopoverTrigger asChild>
                <button className="w-full flex items-center justify-between px-3 py-2 text-sm border border-border rounded bg-card text-foreground hover:bg-muted/50 transition-colors">
                  <span className={dateTo ? "text-foreground" : "text-muted-foreground"}>{dateTo ? format(dateTo, "MMM d, yyyy") : "Select end date"}</span>
                  <CalendarIcon className="h-3.5 w-3.5 opacity-50" />
                </button>
              </PopoverTrigger>
              <PopoverContent className="w-auto p-0" align="start">
                <Calendar mode="single" selected={dateTo} onSelect={setDateTo} className="p-3 pointer-events-auto" />
              </PopoverContent>
            </Popover>
          </div>
        </div>

        <div>
          <label className="text-xs font-medium text-muted-foreground mb-1.5 block">Device</label>
          <MultiSelectDropdown
            label="Devices"
            placeholder="All devices"
            options={deviceOptions}
            selected={devices}
            onChange={setDevices}
            searchPlaceholder="Search devices..."
          />
        </div>

        <div>
          <label className="text-xs font-medium text-muted-foreground mb-1.5 block">Meal Type</label>
          <MultiSelectDropdown
            label="Meal types"
            placeholder="All meal types"
            options={mealOptions}
            selected={meals}
            onChange={setMeals}
            searchPlaceholder="Search meal types..."
          />
        </div>

        <div>
          <label className="text-xs font-medium text-muted-foreground mb-1.5 block">Category</label>
          <MultiSelectDropdown
            label="Categories"
            placeholder="All categories"
            options={categoryOptions}
            selected={categories}
            onChange={setCategories}
            searchPlaceholder="Search categories..."
          />
        </div>

        <div>
          <label className="text-xs font-medium text-muted-foreground mb-1.5 block">Waste Type</label>
          <MultiSelectDropdown
            label="Waste types"
            placeholder="All waste types"
            options={wasteTypeOptions}
            selected={wasteTypes}
            onChange={setWasteTypes}
            searchPlaceholder="Search waste types..."
          />
        </div>

        <div>
          <label className="text-xs font-medium text-muted-foreground mb-1.5 block">Week</label>
          <MultiSelectDropdown
            label="Weeks"
            placeholder="Search and select weeks"
            options={weekOptions}
            selected={weeks}
            onChange={setWeeks}
            searchPlaceholder="Search weeks..."
            enableSearch
          />
        </div>
      </div>

      <div className="px-4 py-3 border-t border-border space-y-2">
        <Button onClick={apply} className="w-full bg-primary text-primary-foreground hover:bg-primary/90 h-9 text-sm">
          Apply Filters
        </Button>
        <Button onClick={reset} variant="outline" className="w-full h-9 text-sm">
          <RotateCcw className="h-3.5 w-3.5 mr-1.5" />
          Reset
        </Button>
      </div>
    </aside>
  );
}
