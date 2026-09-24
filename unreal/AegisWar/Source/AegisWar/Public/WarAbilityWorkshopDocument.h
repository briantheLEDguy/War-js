#pragma once
#include "CoreMinimal.h"
#include "Dom/JsonObject.h"
#include "WarAbilityCatalog.h"

namespace WarWorkshopJson
{
    AEGISWAR_API FString Text(const TSharedPtr<const FJsonObject>& Object,const TCHAR* Key);
    AEGISWAR_API double Number(const TSharedPtr<const FJsonObject>& Object,const TCHAR* Key,double Default=0);
    AEGISWAR_API TSharedPtr<FJsonObject> Object(const TSharedPtr<const FJsonObject>& Parent,const TCHAR* Key);
    AEGISWAR_API const TArray<TSharedPtr<FJsonValue>>& Array(const TSharedPtr<const FJsonObject>& Parent,const TCHAR* Key);
    AEGISWAR_API FString Serialize(const TSharedPtr<const FJsonObject>& Object);
    AEGISWAR_API TSharedPtr<FJsonObject> Parse(const FString& Json);
    AEGISWAR_API TSharedPtr<FJsonObject> Clone(const TSharedPtr<const FJsonObject>& Object);
    AEGISWAR_API TSharedPtr<FJsonObject> Find(const TSharedPtr<const FJsonObject>& Parent,const TCHAR* Collection,const FString& Id);
    AEGISWAR_API bool Numeric(const TSharedPtr<FJsonObject>& Ability,const FString& Path,double& Value,bool bWrite=false);
}

struct FWarWorkshopCellEdit
{
    FString AssignmentId,Path,Operation=TEXT("set");
    double Value=0;
};
struct FWarWorkshopConflict
{
    FString Path;
    TSharedPtr<FJsonValue> Base,Current,Yours;
};
struct FWarWorkshopChange
{
    FString Path;
    TSharedPtr<FJsonValue> Before,After;
};

/** UI document/history has no authority to install combat rules or write shared state. */
class AEGISWAR_API FWarAbilityWorkshopDocument
{
public:
    bool Load(const FString& Json,FString& Error);
    bool Baseline(const TSharedPtr<const FJsonObject>& Manifest,FString& Error);
    const TSharedPtr<FJsonObject>& Get() const { return Current; }
    uint64 Serial() const { return ChangeSerial; }
    bool Commit(const TSharedPtr<FJsonObject>& Candidate,FString& Error);
    bool EditCells(const TArray<FWarWorkshopCellEdit>& Edits,const TSet<FString>& VisibleSelected,FString& Error);
    bool Undo();
    bool Redo();
    void AcknowledgeRevision(int64 Revision);
    static TSharedPtr<FJsonObject> Effective(const TSharedPtr<const FJsonObject>& Workspace,const TSharedPtr<const FJsonObject>& Assignment,FString& Error);
    static bool Compile(const TSharedPtr<const FJsonObject>& Workspace,TArray<FWarAbilityDefinition>& Out,FString& Error,TArray<FWarAbilityDefinition>* Library=nullptr);
    /** Compare stable-ID collections without treating a rename or reorder as deletion. */
    static TArray<FWarWorkshopChange> Changes(const TSharedPtr<FJsonObject>& Before,const TSharedPtr<FJsonObject>& After);
    static TSharedPtr<FJsonObject> Merge(const TSharedPtr<FJsonObject>& Base,const TSharedPtr<FJsonObject>& Current,const TSharedPtr<FJsonObject>& Yours,
        const TMap<FString,bool>& UseYours,TArray<FWarWorkshopConflict>& Conflicts);
private:
    TSharedPtr<FJsonObject> Current;
    TArray<FString> Past,Future;
    uint64 ChangeSerial=0;
};
