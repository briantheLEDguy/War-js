#pragma once
#include "CoreMinimal.h"

struct FWarWorldEditObject
{
    FName Id;
    FTransform Transform;
    bool bHidden = false;
    FString SourceIdentity;
    FName TemplateId;
};

/** Revision-checked construction and edits. Authorization belongs to the server boundary. */
class AEGISWAR_API FWarWorldEditHistory
{
public:
    bool Initialize(const TArray<FWarWorldEditObject>& Objects, FString& Error);
    bool Edit(FName Id, const FTransform& Transform, bool bHidden, int32 ExpectedRevision, FString& Error);
    bool Create(FName Id, FName TemplateId, const FTransform& Transform, int32 ExpectedRevision, FString& Error);
    bool Undo(bool bRedo, int32 ExpectedRevision, FString& Error);
    bool ImportDraft(const FString& Json, int32 ExpectedRevision, FString& Error);
    FString ExportDraft() const;
    int32 GetRevision() const { return Revision; }
    const TArray<FWarWorldEditObject>& GetObjects() const { return Current; }
    const TArray<FWarWorldEditObject>& GetBaselineObjects() const { return Baseline; }
    const FWarWorldEditObject* Find(FName Id) const;
private:
    bool Validate(const TArray<FWarWorldEditObject>& Objects, FString& Error) const;
    bool CheckRevision(int32 Expected, FString& Error) const;
    void Commit(TArray<FWarWorldEditObject> Objects);
    TArray<FWarWorldEditObject> Baseline, Current;
    TArray<TArray<FWarWorldEditObject>> Past, Future;
    int32 Revision = 0;
};
