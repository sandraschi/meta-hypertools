import { ChevronDown, Info, Plus, X } from "lucide-react";
import { useEffect } from "react";

interface JsonSchemaProperty {
  type?: string;
  description?: string;
  default?: unknown;
  enum?: string[];
  items?: {
    type?: string;
  };
}

interface JsonSchema {
  type?: string;
  properties?: Record<string, JsonSchemaProperty>;
  required?: string[];
}

interface DynamicFormProps {
  schema: JsonSchema;
  value: Record<string, unknown>;
  onChange: (value: Record<string, unknown>) => void;
}

function FormLabel({
  htmlId,
  label,
  required,
  description,
}: {
  htmlId: string;
  label: string;
  required: boolean;
  description?: string;
}) {
  return (
    <div className="flex items-center gap-2 mb-1.5">
      <label htmlFor={htmlId} className="text-sm font-medium text-slate-300">
        {label}
      </label>
      {required && (
        <span className="text-[10px] bg-red-500/10 text-red-400 px-1.5 py-0.5 rounded uppercase font-bold tracking-wider">
          Req
        </span>
      )}
      {description && (
        <div className="group relative">
          <Info size={12} className="text-slate-300 cursor-help" />
          <div className="absolute left-0 bottom-full mb-2 w-64 p-2 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-300 shadow-xl opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10">
            {description}
          </div>
        </div>
      )}
    </div>
  );
}

export function DynamicForm({ schema, value, onChange }: DynamicFormProps) {
  // Initialize default values if empty
  useEffect(() => {
    if ((!value || Object.keys(value).length === 0) && schema?.properties) {
      const defaults: Record<string, unknown> = {};
      for (const [key, prop] of Object.entries(schema.properties)) {
        if (prop.default !== undefined) {
          defaults[key] = prop.default;
        }
      }
      if (Object.keys(defaults).length > 0) {
        onChange({ ...value, ...defaults });
      }
    }
  }, [schema, value, onChange]);

  if (!schema?.properties) {
    return (
      <div className="text-slate-300 italic text-sm p-4 text-center">
        No parameters defined for this tool.
      </div>
    );
  }

  const handleChange = (key: string, newValue: unknown) => {
    onChange({ ...value, [key]: newValue });
  };

  const renderField = (key: string, prop: JsonSchemaProperty, required: boolean) => {
    const fieldId = `field-${key}`;
    const currentValue = value?.[key];

    // ENUM
    if (prop.enum) {
      return (
        <div key={key} className="mb-4">
          <FormLabel
            htmlId={fieldId}
            label={key}
            required={required}
            description={prop.description}
          />
          <div className="relative">
            <select
              id={fieldId}
              value={(currentValue as string) ?? ""}
              onChange={(e) => handleChange(key, e.target.value)}
              className="w-full appearance-none bg-slate-900 border border-slate-700 text-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50"
            >
              <option value="">Select an option...</option>
              {prop.enum.map((opt: string) => (
                <option key={opt} value={opt}>
                  {opt}
                </option>
              ))}
            </select>
            <ChevronDown
              className="absolute right-3 top-2.5 text-slate-300 pointer-events-none"
              size={16}
            />
          </div>
        </div>
      );
    }

    // BOOLEAN
    if (prop.type === "boolean") {
      return (
        <div key={key} className="mb-4">
          <FormLabel
            htmlId={fieldId}
            label={key}
            required={required}
            description={prop.description}
          />
          <div className="flex items-center justify-between p-3 bg-slate-900/50 rounded-lg border border-slate-800">
            <div className="flex flex-col">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-slate-300">{key}</span>
                {required && <span className="text-red-400">*</span>}
              </div>
              {prop.description && (
                <span className="text-xs text-slate-300 mt-0.5">{prop.description}</span>
              )}
            </div>
            <button
              type="button"
              id={fieldId}
              onClick={() => handleChange(key, !currentValue)}
              className={`w-12 h-6 rounded-full transition-colors relative ${
                currentValue ? "bg-blue-600" : "bg-slate-700"
              }`}
              aria-checked={!!currentValue}
              role="switch"
            >
              <div
                className={`absolute top-1 w-4 h-4 rounded-full bg-white transition-transform ${
                  currentValue ? "left-7" : "left-1"
                }`}
              />
            </button>
          </div>
        </div>
      );
    }

    // ARRAY (Simple List of strings)
    if (prop.type === "array" && (prop.items?.type === "string" || !prop.items)) {
      const items = Array.isArray(currentValue) ? (currentValue as string[]) : [];

      return (
        <div key={key} className="mb-4">
          <FormLabel
            htmlId={fieldId}
            label={key}
            required={required}
            description={prop.description}
          />
          <div className="space-y-2">
            {items.map((item: string, idx: number) => {
              const itemKey = `${fieldId}-item-${idx}-${item.length}`;
              return (
                <div key={itemKey} className="flex gap-2">
                  <input
                    id={`${fieldId}-${idx}`}
                    type="text"
                    value={item}
                    onChange={(e) => {
                      const newItems = [...items];
                      newItems[idx] = e.target.value;
                      handleChange(key, newItems);
                    }}
                    className="flex-1 bg-slate-900 border border-slate-700 text-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50"
                  />
                  <button
                    type="button"
                    onClick={() => {
                      const newItems = items.filter((_, i) => i !== idx);
                      handleChange(key, newItems);
                    }}
                    className="p-2 text-slate-300 hover:text-red-400 hover:bg-slate-800 rounded-lg transition-colors"
                    aria-label={`Remove item ${idx + 1}`}
                  >
                    <X size={16} />
                  </button>
                </div>
              );
            })}
            <button
              type="button"
              onClick={() => handleChange(key, [...items, ""])}
              className="flex items-center gap-2 text-xs text-blue-400 hover:text-blue-300 font-medium px-2 py-1 hover:bg-blue-500/10 rounded transition-colors"
            >
              <Plus size={14} /> Add Item
            </button>
          </div>
        </div>
      );
    }

    // OBJECT (Fallback to JSON string input)
    if (prop.type === "object") {
      return (
        <div key={key} className="mb-4">
          <FormLabel
            htmlId={fieldId}
            label={key}
            required={required}
            description={prop.description}
          />
          <textarea
            id={fieldId}
            value={
              typeof currentValue === "object" && currentValue !== null
                ? JSON.stringify(currentValue, null, 2)
                : String(currentValue ?? "")
            }
            onChange={(e) => {
              try {
                const parsed = JSON.parse(e.target.value);
                handleChange(key, parsed);
              } catch {
                handleChange(key, e.target.value);
              }
            }}
            className="w-full bg-slate-900 border border-slate-700 text-slate-200 rounded-lg px-3 py-2 text-xs font-mono focus:outline-none focus:ring-2 focus:ring-blue-500/50 min-h-[80px]"
            placeholder="{ ... }"
          />
          <p className="text-[10px] text-slate-300 mt-1">Type valid JSON for object properties.</p>
        </div>
      );
    }

    // STRING / NUMBER / INTEGER
    return (
      <div key={key} className="mb-4">
        <FormLabel
          htmlId={fieldId}
          label={key}
          required={required}
          description={prop.description}
        />
        <input
          id={fieldId}
          type={prop.type === "integer" || prop.type === "number" ? "number" : "text"}
          value={(currentValue as string) ?? ""}
          onChange={(e) => {
            const val = e.target.value;
            if (prop.type === "integer") {
              handleChange(key, Number.parseInt(val, 10) || 0);
            } else if (prop.type === "number") {
              handleChange(key, Number.parseFloat(val) || 0);
            } else {
              handleChange(key, val);
            }
          }}
          className="w-full bg-slate-900 border border-slate-700 text-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50 placeholder:text-slate-600"
          placeholder={`Enter ${key}...`}
        />
      </div>
    );
  };

  return (
    <div className="space-y-2">
      {Object.entries(schema.properties || {}).map(([key, prop]) =>
        renderField(key, prop, schema.required?.includes(key) || false),
      )}
    </div>
  );
}
