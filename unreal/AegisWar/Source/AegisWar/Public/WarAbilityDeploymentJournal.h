#pragma once
#include "CoreMinimal.h"
#include "Dom/JsonObject.h"

/** Personal development versions. An exclusive writer lock spans the running session. */
class AEGISWAR_API FWarAbilityDeploymentJournal
{
public:
    bool Open(const FString& Directory,FString& Error);
    bool Queue(const TSharedPtr<FJsonObject>& Document,const FString& Name,FString& Version,FString& Error);
    bool QueueExisting(const FString& Version,const FString& Name,FString& Error);
    bool Complete(const FString& Version,FString& Error);
    bool Fail(const FString& Reason,FString& Error);
    TSharedPtr<FJsonObject> ReadVersion(const FString& Version,FString& Error) const;
    FString Active() const;
    FString Pending() const;
    const TArray<TSharedPtr<FJsonValue>>& Records() const;
private:
    FString Folder;
    TUniquePtr<FArchive> WriterLock;
    TSharedPtr<FJsonObject> State;
    bool Save(const TSharedPtr<FJsonObject>& Candidate,FString& Error);
    static bool ValidId(const FString& Value);
};
