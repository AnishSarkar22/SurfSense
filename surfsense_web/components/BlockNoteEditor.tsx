"use client";

import { useEffect, useRef, useMemo, useState } from "react";
import { useTheme } from "next-themes";
import "@blocknote/core/fonts/inter.css";
import "@blocknote/mantine/style.css";
import { useCreateBlockNote } from "@blocknote/react";
import { BlockNoteView } from "@blocknote/mantine";

interface BlockNoteEditorProps {
  initialContent?: any;
  onChange?: (content: any) => void;
}

export default function BlockNoteEditor({
  initialContent,
  onChange,
}: BlockNoteEditorProps) {
  // Track the initial content to prevent re-initialization
  const initialContentRef = useRef<any>(null);
  const isInitializedRef = useRef(false);
  
  const { resolvedTheme, theme } = useTheme();
  const [mounted, setMounted] = useState(false);

  // Prevent hydration issues
  useEffect(() => {
    setMounted(true);
  }, []);

  // Determine BlockNote theme based on current theme
  const blockNoteTheme = useMemo(() => {
    if (!mounted) return "light"; // Default to light during SSR
    const isDark = resolvedTheme === "dark" || theme === "dark";
    return isDark ? "dark" : "light";
  }, [mounted, resolvedTheme, theme]);
  
  // Creates a new editor instance - only use initialContent on first render
  const editor = useCreateBlockNote({
    initialContent: initialContentRef.current === null ? (initialContent || undefined) : undefined,
  });
  
  // Store initial content on first render only
  useEffect(() => {
    if (initialContent && initialContentRef.current === null) {
      initialContentRef.current = initialContent;
      isInitializedRef.current = true;
    }
  }, [initialContent]);

  // Call onChange when document changes (but don't update from props)
  useEffect(() => {
    if (!onChange || !editor || !isInitializedRef.current) return;
    
    const handleChange = () => {
      onChange(editor.document);
    };
    
    // Subscribe to document changes
    const unsubscribe = editor.onChange(handleChange);
    
    return () => {
      unsubscribe();
    };
  }, [editor, onChange]);

  // Renders the editor instance with theme support
  return <BlockNoteView editor={editor} theme={blockNoteTheme} />;
}
