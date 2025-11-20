"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Loader2, ArrowLeft, Save, CheckCircle2, AlertCircle } from "lucide-react";
import { useTranslations } from "next-intl";
import { BlockNoteEditor } from "@/components/DynamicBlockNoteEditor";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";

interface EditorContent {
  document_id: number;
  title: string;
  blocknote_document: any;
  is_collaborative: boolean;
  collaboration_session_id: string | null;
  last_edited_at: string | null;
}

export default function EditorPage() {
  const params = useParams();
  const router = useRouter();
  const documentId = params.documentId as string;
  const t = useTranslations("common");
  
  const [document, setDocument] = useState<EditorContent | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [editorContent, setEditorContent] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [lastSaved, setLastSaved] = useState<Date | null>(null);
  const [autoSaveStatus, setAutoSaveStatus] = useState<"idle" | "saving" | "saved">("idle");
  
  // Get auth token
  const token = typeof window !== "undefined" 
    ? localStorage.getItem("surfsense_bearer_token") 
    : null;
  
  // Fetch document content - DIRECT CALL TO FASTAPI
  useEffect(() => {
    async function fetchDocument() {
      if (!token) {
        console.error("No auth token found");
        setError("Please login to access the editor");
        setLoading(false);
        return;
      }
      
      try {
        const response = await fetch(
          `${process.env.NEXT_PUBLIC_FASTAPI_BACKEND_URL}/api/v1/documents/${documentId}/editor-content`,
          {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          }
        );
        
        if (!response.ok) {
          const errorData = await response.json().catch(() => ({ detail: "Failed to fetch document" }));
          throw new Error(errorData.detail || "Failed to fetch document");
        }
        
        const data = await response.json();
        
        // Check if blocknote_document exists
        if (!data.blocknote_document) {
          setError("This document does not have BlockNote content. Please re-upload the document to enable editing.");
          setLoading(false);
          return;
        }
        
        setDocument(data);
        setEditorContent(data.blocknote_document);
        setError(null);
      } catch (error) {
        console.error("Error fetching document:", error);
        setError(error instanceof Error ? error.message : "Failed to fetch document. Please try again.");
      } finally {
        setLoading(false);
      }
    }
    
    if (documentId && token) {
      fetchDocument();
    }
  }, [documentId, token]);
  
  // Auto-save every 30 seconds - FASTAPI backend call
  useEffect(() => {
    if (!editorContent || !token || !document) return;
    
    const interval = setInterval(async () => {
      setAutoSaveStatus("saving");
      try {
        const response = await fetch(
          `${process.env.NEXT_PUBLIC_FASTAPI_BACKEND_URL}/api/v1/documents/${documentId}/blocknote-content`,
          {
            method: "PUT",
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify({ blocknote_document: editorContent }),
          }
        );
        
        if (response.ok) {
          setLastSaved(new Date());
          setAutoSaveStatus("saved");
          setTimeout(() => setAutoSaveStatus("idle"), 2000);
        } else {
          setAutoSaveStatus("idle");
        }
      } catch (error) {
        console.error("Auto-save failed:", error);
        setAutoSaveStatus("idle");
      }
    }, 30000); // 30 seconds
    
    return () => clearInterval(interval);
  }, [editorContent, documentId, token, document]);
  
  // Save and exit - DIRECT CALL TO FASTAPI
  const handleSave = async () => {
    if (!token) {
      alert("Please login to save");
      return;
    }
    
    if (!editorContent) {
      alert("No content to save");
      return;
    }
    
    setSaving(true);
    try {
      // Save blocknote_document to database (without finalizing/reindexing)
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_FASTAPI_BACKEND_URL}/api/v1/documents/${documentId}/blocknote-content`,
        {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ blocknote_document: editorContent }),
        }
      );
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: "Failed to save document" }));
        throw new Error(errorData.detail || "Failed to save document");
      }
      
      // Redirect back to documents list
      router.push(`/dashboard/${params.search_space_id}/documents`);
    } catch (error) {
      console.error("Error saving document:", error);
      alert(error instanceof Error ? error.message : "Failed to save document. Please try again.");
    } finally {
      setSaving(false);
    }
  };
  
  // Loading state
  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-4">
        <Card className="w-[400px] bg-background/60 backdrop-blur-sm">
          <CardHeader className="pb-2">
            <CardTitle className="text-xl font-medium">{t("loading")}</CardTitle>
            <CardDescription>Loading document editor...</CardDescription>
          </CardHeader>
          <CardContent className="flex justify-center py-6">
            <Loader2 className="h-12 w-12 text-primary animate-spin" />
          </CardContent>
        </Card>
      </div>
    );
  }
  
  // Error state
  if (error) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-4 p-4">
        <Card className="w-full max-w-md bg-background/60 backdrop-blur-sm border-destructive/20">
          <CardHeader className="pb-2">
            <div className="flex items-center gap-2">
              <AlertCircle className="h-5 w-5 text-destructive" />
              <CardTitle className="text-xl font-medium text-destructive">
                {t("error")}
              </CardTitle>
            </div>
            <CardDescription className="text-destructive/80">{error}</CardDescription>
          </CardHeader>
          <CardContent className="pt-4">
            <Button
              type="button"
              variant="outline"
              onClick={() => router.back()}
              className="w-full"
            >
              <ArrowLeft className="h-4 w-4 mr-2" />
              {t("back")}
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }
  
  if (!document) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-4">
        <Card className="w-[400px]">
          <CardHeader>
            <CardTitle>Document not found</CardTitle>
            <CardDescription>The document you're looking for doesn't exist.</CardDescription>
          </CardHeader>
          <CardContent>
            <Button
              type="button"
              variant="outline"
              onClick={() => router.back()}
              className="w-full"
            >
              <ArrowLeft className="h-4 w-4 mr-2" />
              {t("back")}
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }
  
  const formatLastSaved = (date: Date) => {
    const now = new Date();
    const diff = Math.floor((now.getTime() - date.getTime()) / 1000);
    
    if (diff < 60) return "Just now";
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return date.toLocaleDateString();
  };
  
  return (
    <div className="flex flex-col h-full bg-background">
      {/* Toolbar */}
      <div className="border-b bg-card/50 backdrop-blur-sm sticky top-0 z-10">
        <div className="container mx-auto px-4 py-3">
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-3 min-w-0 flex-1">
              <Button
                type="button"
                variant="ghost"
                size="icon"
                onClick={() => router.back()}
                className="shrink-0"
              >
                <ArrowLeft className="h-4 w-4" />
              </Button>
              <Separator orientation="vertical" className="h-6" />
              <div className="min-w-0 flex-1">
                <h1 className="text-lg font-semibold truncate">{document.title}</h1>
                {lastSaved && (
                  <p className="text-xs text-muted-foreground">
                    Last saved {formatLastSaved(lastSaved)}
                  </p>
                )}
              </div>
            </div>
            
            <div className="flex items-center gap-3 shrink-0">
              {/* Auto-save status indicator */}
              {autoSaveStatus === "saving" && (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Loader2 className="h-3 w-3 animate-spin" />
                  <span className="hidden sm:inline">Saving...</span>
                </div>
              )}
              {autoSaveStatus === "saved" && (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <CheckCircle2 className="h-3 w-3 text-green-600" />
                  <span className="hidden sm:inline">Saved</span>
                </div>
              )}
              
              <Button
                type="button"
                variant="outline"
                onClick={() => router.back()}
                className="hidden sm:flex"
              >
                {t("cancel")}
              </Button>
              <Button
                type="button"
                onClick={handleSave}
                disabled={saving}
                className="gap-2"
              >
                {saving ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    <span className="hidden sm:inline">Saving...</span>
                  </>
                ) : (
                  <>
                    <Save className="h-4 w-4" />
                    <span>Save & Exit</span>
                  </>
                )}
              </Button>
            </div>
          </div>
        </div>
      </div>
      
      {/* Editor */}
      <div className="flex-1 overflow-auto dark:bg-[#1F1F1F]">
        <div className="container mx-auto px-4 py-6 max-w-4xl">
          <BlockNoteEditor
            initialContent={editorContent}
            onChange={setEditorContent}
          />
        </div>
      </div>
    </div>
  );
}
