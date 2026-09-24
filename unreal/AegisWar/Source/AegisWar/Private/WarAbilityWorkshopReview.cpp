#include "WarAbilityWorkshopDocument.h"

using namespace WarWorkshopJson;

TArray<FWarWorkshopChange> FWarAbilityWorkshopDocument::Changes(const TSharedPtr<FJsonObject>& Before,const TSharedPtr<FJsonObject>& After)
{
    TArray<FWarWorkshopChange> Result;
    TFunction<void(TSharedPtr<FJsonValue>,TSharedPtr<FJsonValue>,FString)> Visit;
    Visit=[&](TSharedPtr<FJsonValue> B,TSharedPtr<FJsonValue> A,FString Path) {
        if ((!B && !A) || (B && A && FJsonValue::CompareEqual(*B,*A))) return;
        if ((!B || B->Type==EJson::Object) && (!A || A->Type==EJson::Object))
        {
            TArray<FString> Keys;
            for (const auto& V:{B,A}) if (V) for (const auto& Pair:V->AsObject()->Values) Keys.AddUnique(FString(Pair.Key));
            Keys.Sort();
            if (Keys.IsEmpty()) { Result.Add({Path,B,A}); return; }
            for (const auto& Key:Keys) Visit(B ? B->AsObject()->TryGetField(Key) : nullptr,A ? A->AsObject()->TryGetField(Key) : nullptr,Path+TEXT("/")+Key);
            return;
        }
        if ((!B || B->Type==EJson::Array) && (!A || A->Type==EJson::Array))
        {
            TMap<FString,TSharedPtr<FJsonValue>> Maps[2]; TArray<FString> Order[2]; bool Identified=true; int32 Index=0;
            const TArray<TSharedPtr<FJsonValue>> Empty;
            for (const auto& V:{B,A}) { for (const auto& Item:V ? V->AsArray() : Empty) {
                if (Item->Type!=EJson::Object) { Identified=false; break; }
                FString Id=Text(Item->AsObject(),TEXT("id")); if (Id.IsEmpty()) Id=Text(Item->AsObject(),TEXT("path"));
                if (Id.IsEmpty() || Maps[Index].Contains(Id)) { Identified=false; break; }
                Maps[Index].Add(Id,Item); Order[Index].Add(Id);
            } ++Index; }
            if (Identified)
            {
                TArray<FString> Keys=Order[0]; for (const auto& Key:Order[1]) Keys.AddUnique(Key); Keys.Sort();
                for (const auto& Key:Keys) Visit(Maps[0].FindRef(Key),Maps[1].FindRef(Key),Path+TEXT("/")+Key);
                TArray<FString> Common[2];
                for (int32 I=0;I<2;++I) for (const auto& Key:Order[I]) if (Maps[0].Contains(Key) && Maps[1].Contains(Key)) Common[I].Add(Key);
                if (Common[0]!=Common[1]) {
                    TSharedPtr<FJsonValue> Values[2];
                    for (int32 I=0;I<2;++I) { TArray<TSharedPtr<FJsonValue>> Ids; for (const auto& Key:Order[I]) Ids.Add(MakeShared<FJsonValueString>(Key)); Values[I]=MakeShared<FJsonValueArray>(Ids); }
                    Result.Add({Path+TEXT("/@order"),Values[0],Values[1]});
                }
                return;
            }
            const auto& Left=B ? B->AsArray() : Empty; const auto& Right=A ? A->AsArray() : Empty;
            for (int32 I=0;I<FMath::Max(Left.Num(),Right.Num());++I) Visit(Left.IsValidIndex(I) ? Left[I] : nullptr,Right.IsValidIndex(I) ? Right[I] : nullptr,Path+TEXT("/")+FString::FromInt(I+1));
            return;
        }
        Result.Add({Path,B,A});
    };
    TSharedPtr<FJsonValue> B,A;
    if (Before) B=MakeShared<FJsonValueObject>(Before);
    if (After) A=MakeShared<FJsonValueObject>(After);
    Visit(B,A,TEXT(""));
    return Result;
}
