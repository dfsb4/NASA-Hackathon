import React, { useState, useEffect, useRef } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useLocation } from "react-router-dom";

const GeminiChat = () => {
  const location = useLocation();
  const initialPrompt = location.state?.initialPrompt || "";

  const [input, setInput] = useState("");
  const [messages, setMessages] = useState([]);
  const API_KEY = "YOUR_GEMINI_API_KEY";

  const hasSentInitialMessage = useRef(false); // to prevent sending multiple initial messages

  //initial prompt
  useEffect(() => {
    if (initialPrompt && !hasSentInitialMessage.current) {
      hasSentInitialMessage.current = true;
      const initialUserMessage = {
        role: "user",
        content: initialPrompt,
      };
      // setMessages([initialUserMessage]);
  
      // Send initial message to the bot
      const sendInitialMessage = async () => {
        try {
          const response = await fetch("http://127.0.0.1:5000/api/nasa", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ input: initialPrompt }),
          });
          const data = await response.json();
  
          const botMessage = {
            role: "bot",
            content: data.response || "No response",
          };
  
          setMessages((prev) => [...prev, botMessage]);
        } catch (error) {
          console.error("Error fetching initial response:", error);
        }
      };
  
      sendInitialMessage();
    }
  }, [initialPrompt]);
  

  const sendMessage = async () => {
    if (!input.trim()) return;

    const userMessage = { role: "user", content: input };
    setMessages([...messages, userMessage]);
    setInput("");

    try {
      const response = await fetch("http://127.0.0.1:5000/api/nasa", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ input }),
      });
      const data = await response.json();
      
      // for Gemini API
      // const botMessage = {
      //   role: "bot",
      //   content: data.candidates?.[0]?.content?.parts?.[0]?.response || "No response"
      // };


      // for RAG
      const botMessage = {
        role: "bot",
        content: data.response || "No response"
      };
      
      
      setMessages([...messages, userMessage, botMessage]);
    } catch (error) {
      console.error("Error fetching response:", error);
    }
  };

  return (
    <div>
      <p className="p-4 text-lg">
        Send and receive messages as stylish postcards—same API, new look.
      </p>

      <div className="h-screen flex flex-col bg-gray-100">
        <div className="flex-1 overflow-y-auto p-4">
          <Card className="h-full">
            <CardContent className="h-full flex flex-col">
              <div className="flex-1 overflow-y-auto p-4 bg-white rounded-lg">
                {/* Airmail top ribbon */}
                <div className="h-2 w-full rounded mb-4 bg-[repeating-linear-gradient(45deg,_#e11d48_0_12px,_#0ea5e9_12px_24px,_#f8fafc_24px_36px)]" />

                {messages.map((msg, index) => (
                  <div key={index} className="mb-6">
                    <Card className="relative w-full border-[3px] border-gray-300 shadow-sm">
                      {/* Faux stamp */}
                      <div className="absolute top-3 right-3 w-16 h-16 border-2 border-gray-400 grid place-items-center rotate-6 text-[10px] font-semibold tracking-widest text-gray-500 bg-white">
                        STAMP
                      </div>

                      {/* Postcard grid */}
                      <div className="grid grid-cols-1 md:grid-cols-2">
                        {/* Message side (left) */}
                        <div className="p-5 md:border-r md:border-dashed md:border-gray-300">
                          <div className="text-xs uppercase tracking-wider text-gray-500 mb-2">
                            {msg.role === "user" ? "From: You" : "From: Gemini"}
                          </div>
                          <div className="font-serif text-2xl mb-3">
                            Postcard
                          </div>

                          <div className="prose prose-sm max-w-none">
                            <ReactMarkdown remarkPlugins={[remarkGfm]}>
                              {msg.content}
                            </ReactMarkdown>
                          </div>
                        </div>

                        {/* Address side (right) */}
                        <div className="p-5 bg-slate-50/60">
                          <div className="flex items-center justify-between mb-3">
                            <div className="text-xs uppercase tracking-wider text-gray-500">
                              To: {msg.role === "user" ? "Gemini" : "You"}
                            </div>
                            {/* Airmail tag */}
                            <span className="px-2 py-1 text-[10px] rounded border border-gray-300 tracking-widest">
                              AIR MAIL ✈️
                            </span>
                          </div>

                          {/* Address lines */}
                          <div className="space-y-4 mt-4">
                            <div className="h-0.5 bg-gray-200" />
                            <div className="h-0.5 bg-gray-200" />
                            <div className="h-0.5 bg-gray-200" />
                            <div className="h-0.5 bg-gray-200" />
                            <div className="h-0.5 bg-gray-200" />
                          </div>

                          {/* Postmark */}
                          <div className="mt-6 flex items-center gap-2 text-[10px] text-gray-500">
                            <span className="inline-block w-10 h-10 rounded-full border-2 border-gray-300 grid place-items-center">
                              ✷
                            </span>
                            <span className="tracking-widest">
                              POSTMARK • VIA API
                            </span>
                          </div>
                        </div>
                      </div>
                    </Card>
                  </div>
                ))}

                {/* Airmail bottom ribbon */}
                <div className="h-2 w-full rounded mt-2 bg-[repeating-linear-gradient(45deg,_#e11d48_0_12px,_#0ea5e9_12px_24px,_#f8fafc_24px_36px)]" />
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Input row 保持不變 */}
        <div className="p-4 bg-white border-t flex items-center space-x-2">
          <Input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ex: Plan a trip to Bangkok for 5 days"
            className="flex-1"
          />
          <Button onClick={sendMessage}>Send</Button>
        </div>
      </div>
    </div>
  );

};

export default GeminiChat;
